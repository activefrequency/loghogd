import socket, select, struct, zlib, ssl, logging
from ext.groper import define_opt, options

from util import parse_addrs, format_connection_message

define_opt('server', 'default_port', type=int, default=5566)

define_opt('server', 'listen_ipv4', default='127.0.0.1')
define_opt('server', 'listen_ipv6', default='[::1]')

define_opt('server', 'pemfile', default='')
define_opt('server', 'cacert', default='')

class Server(object):
    STREAM_SOCKET_BACKLOG = 5
    MAX_MSG_SIZE = 1024*8

    BUFSIZE = 4096
    _FLAGS_GZIP = 0x01
    
    HEADER_FORMAT = '!LL'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MSG_FORMAT_PROTO = '%ds'

    def __init__(self, callback, listen_ipv4=None, listen_ipv6=None, default_port=None):
        self.log = logging.getLogger('server') # internal logger

        self.callback = callback
        self.closed = False

        self.stream_socks = set()
        self.dgram_socks = set()

        self.client_stream_socks = set()
        self.stream_buffers = {}

        self.client_socket_addrs = {}

        listen_ipv4 = listen_ipv4 if listen_ipv4 is not None else options.server.listen_ipv4
        listen_ipv6 = listen_ipv6 if listen_ipv6 is not None else options.server.listen_ipv6
        default_port = default_port if default_port is not None else options.server.default_port
        
        ipv4_addrs = parse_addrs(listen_ipv4, default_port)
        ipv6_addrs = parse_addrs(listen_ipv6, default_port)

        for addr in ipv4_addrs:
            self.stream_socks.add(self.connect(addr, socket.AF_INET, socket.SOCK_STREAM))
            self.dgram_socks.add(self.connect(addr, socket.AF_INET, socket.SOCK_DGRAM))

        for addr in ipv6_addrs:
            self.stream_socks.add(self.connect(addr, socket.AF_INET6, socket.SOCK_STREAM))
            self.dgram_socks.add(self.connect(addr, socket.AF_INET6, socket.SOCK_DGRAM))

        self.all_socks = set(self.stream_socks | self.dgram_socks)

    def connect(self, address, family, proto):
        '''Returns a socket for a given addres, family and protocol.'''

        self.log.info(format_connection_message(address, family, proto))
        sock = socket.socket(family, proto)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(address)

        if proto == socket.SOCK_STREAM:
            sock.listen(self.STREAM_SOCKET_BACKLOG)

        return sock

    def run(self):
        '''Runs the main loop, collecting data and sending it to the callback.'''

        while True:
            try:
                r, w, e = select.select(self.all_socks, [], self.all_socks)
            except Exception as exc:
                if self.closed:
                    break
                elif isinstance(exc, select.error) and exc.args[0] == 4:
                    continue # Got signal, probably HUP
                else:
                    raise

            for sock in e:
                # Disconnect error streams
                self.disconnect_client_stream(sock)

            for sock in r:
                if sock in self.dgram_socks:
                    # Receive datagram
                    msg, addr = sock.recvfrom(self.MAX_MSG_SIZE)
                    payload, _ = self.parse_datagram(msg)
                    self.callback(payload, addr)

                elif sock in self.stream_socks:
                    # Accept new stream
                    clientsock, addr = sock.accept()
                    try:
                        self.connect_client_stream(clientsock, addr)
                    except (socket.error, ssl.SSLError) as e:
                        self.log.exception(e)

                elif sock in self.client_stream_socks:
                    # Read client data
                    data = sock.read(self.BUFSIZE) if isinstance(sock, ssl.SSLSocket) else sock.recv(self.BUFSIZE)
                    if data:
                        self.stream_buffers[sock].append(data)
                    
                    for msg in self.parse_stream_buffer(sock):
                        self.callback(msg, self.client_socket_addrs[sock])

                    if not data:
                        self.disconnect_client_stream(sock)

    def connect_client_stream(self, sock, addr):
        '''Adds a new socket to the list of stream sockets.'''

        try:
            if options.server.pemfile:
                sock = ssl.wrap_socket(sock,
                    keyfile=options.server.pemfile,
                    certfile=options.server.pemfile,
                    ca_certs=options.server.cacert,
                    server_side=True,
                    cert_reqs=ssl.CERT_REQUIRED,
                )

            self.client_socket_addrs[sock] = addr
            self.client_stream_socks.add(sock)
            self.all_socks.add(sock)
            self.stream_buffers[sock] = []
        except Exception as e:
            self.disconnect_client_stream(sock)
            self.log.exception(e)

    def disconnect_client_stream(self, sock):
        '''Removes all references to a client stream.'''

        if sock in self.client_stream_socks:
            self.client_stream_socks.remove(sock)

        if sock in self.all_socks:
            self.all_socks.remove(sock)
        
        if sock in self.client_socket_addrs:
            del self.client_socket_addrs[sock]

        if sock in self.stream_buffers:
            del self.stream_buffers[sock]

        try:
            sock.close()
        except socket.error:
            pass

    def parse_stream_buffer(self, sock):
        '''Parses all the complete packets from the buffer and returns a generator.'''

        buf = ''.join(self.stream_buffers[sock])
        if len(buf) < self.HEADER_SIZE:
            return

        while True:
            if len(buf) > self.HEADER_SIZE:
                payload, buf = self.parse_datagram(buf)
                if payload:
                    yield payload
                else:
                    break
            else:
                break

        self.stream_buffers[sock] = [] if not buf else [buf]

    def parse_datagram(self, buf):
        '''If the buf bytestring contains a full datagram, extracts and parses it.

        This method returns a 2-tuple of (payload, buf) where the payload is a
        bytestring payload of the datagram, with the wire-protocol headers stripped,
        and buf - the modified buffer with the datagram removed.

        If the passed-in buf does not contain a full datagram, (None, None) is returned.'''

        # XXX: should we detect incomplete datagrams preceeding complete datagrams?

        size, flags = struct.unpack(self.HEADER_FORMAT, buf[:self.HEADER_SIZE])
        if len(buf) >= self.HEADER_SIZE + size:
            payload = struct.unpack(self.MSG_FORMAT_PROTO % size, buf[self.HEADER_SIZE:])[0]
            buf = buf[self.HEADER_SIZE + size:]

            if flags & self._FLAGS_GZIP:
                payload = zlib.decompress(payload)

            return payload, buf
        else:
            return None, None

    def close(self):
        '''Closes all open sockets.'''

        # XXX: this does not allow for re-loading the config file

        for sock in self.all_socks:
            sock.close()
            
        self.closed = True

