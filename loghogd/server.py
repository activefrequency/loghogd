import socket, select, struct, zlib, ssl, logging, os, time
from ext.groper import define_opt, options

from util import parse_addrs, format_connection_message, normalize_path

define_opt('server', 'default_port', type=int, default=5566)
define_opt('server', 'listen_ipv4', default='127.0.0.1')
define_opt('server', 'listen_ipv6', default='[::1]')

define_opt('server', 'default_port_ssl', type=int, default=5577)
define_opt('server', 'listen_ipv4_ssl', default='')
define_opt('server', 'listen_ipv6_ssl', default='')

define_opt('server', 'pemfile', default='')
define_opt('server', 'cacert', default='')

class ServerError(Exception):
    '''Raised when the server experiences an error.'''

class ServerStartupError(Exception):
    '''Raised when the server cannot start.'''

class Server(object):
    '''Main server class.

    A single instance of this class typically acts as the event loop for LogHog.
    The main event loop is implemented in the run() method.
    '''
    
    SHUTDOWN_TIMEOUT = 0.25 # small timeout between socket.shutdown() and socket.close()

    STREAM_SOCKET_BACKLOG = 5
    MAX_MSG_SIZE = 1024*8

    BUFSIZE = 4096
    _FLAGS_GZIP = 0x01
    
    HEADER_FORMAT = '!LL'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MSG_FORMAT_PROTO = '%ds'

    def __init__(self, callback, conf_root, listen_ipv4=None, listen_ipv6=None, default_port=None, listen_ipv4_ssl=None, listen_ipv6_ssl=None, default_port_ssl=None, pemfile=None, cacert=None):
        '''Initializes the server and listens on the specified addresses.

        param callback : callable
            The callable that is called as callabale(msg, addr) whenever a message is received.
        param conf_root : unicode
            Path to the root of the configuration tree
        param listen_ipv4 : comma separated basestring of addresses
            Addresses to listen on for TCP and UDP connections
        param listen_ipv6 : comma separated basestring of addresses
            Addresses to listen on for TCP and UDP connections
        param default_port : short
            Port to use for listen_ipv4 and listen_ipv6 if they don't specify a custom port
        param listen_ipv4_ssl : comma separated basestring of addresses
            Addresses to listen on for SSL/TLS connections
        param listen_ipv6_ssl : comma separated basestring of addresses
            Addresses to listen on for SSL/TLS connections
        param default_port_ssl : short
            Port to use for listen_ipv4_ssl and listen_ipv6_ssl if they don't specify a custom port
        param pemfile : unicode
            File path to the pem file containing private and public keys for SSL/TLS
        param cacert : unicode
            File path to the cacert file with which the public key in pemfile is signed
        '''

        self.log = logging.getLogger('server') # internal logger

        self.callback = callback
        self.closed = False

        self.stream_socks = set()
        self.ssl_socks = set()
        self.dgram_socks = set()

        self.client_stream_socks = set()
        self.stream_buffers = {}

        self.client_socket_addrs = {}

        self.select_timeout = None # Set on shutdown to prevent infinite wait

        self.pemfile = normalize_path(pemfile if pemfile is not None else options.server.pemfile, conf_root)
        self.cacert = normalize_path(cacert if cacert is not None else options.server.cacert, conf_root)

        # Initialize server sockets
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

        # Same thing for SSL addresses, except not datagram sockets
        listen_ipv4_ssl = listen_ipv4_ssl if listen_ipv4_ssl is not None else options.server.listen_ipv4_ssl
        listen_ipv6_ssl = listen_ipv6_ssl if listen_ipv6_ssl is not None else options.server.listen_ipv6_ssl
        default_port_ssl = default_port_ssl if default_port_ssl is not None else options.server.default_port_ssl

        self.validate_ssl_config(listen_ipv4_ssl, listen_ipv6_ssl)
        
        ipv4_addrs_ssl = parse_addrs(listen_ipv4_ssl, default_port_ssl)
        ipv6_addrs_ssl = parse_addrs(listen_ipv6_ssl, default_port_ssl)

        for addr in ipv4_addrs_ssl:
            s = self.connect(addr, socket.AF_INET, socket.SOCK_STREAM, True)
            self.stream_socks.add(s)
            self.ssl_socks.add(s)

        for addr in ipv6_addrs_ssl:
            s = self.connect(addr, socket.AF_INET6, socket.SOCK_STREAM, True)
            self.stream_socks.add(s)
            self.ssl_socks.add(s)

        self.all_socks = set(self.stream_socks | self.dgram_socks)

    def validate_ssl_config(self, listen_ipv4_ssl, listen_ipv6_ssl):
        '''Validates all SSL options at startup to prevent runtime errors.

        This method raises a ServerException if it finds an issue.'''

        if (len(listen_ipv4_ssl) + len(listen_ipv6_ssl)) == 0:
            return

        if not self.pemfile:
            raise ServerStartupError('Configuration for server.pemfile is not specified, but we are supposed to listen for SSL connections.')
    
        if not self.cacert:
            raise ServerStartupError('Configuration for server.cacert is not specified, but we are supposed to listen for SSL connections.')
        
        if not os.path.exists(self.pemfile):
            raise ServerStartupError('server.pemfile file does not exist: {0}'.format(self.pemfile))
        
        if not os.path.exists(self.cacert):
            raise ServerStartupError('server.cacert file does not exist: {0}'.format(self.pemfile))

        if not os.access(self.pemfile, os.R_OK):
            raise ServerStartupError('{0} is not readable by the current user.'.format(self.pemfile))

        if not os.access(self.cacert, os.R_OK):
            raise ServerStartupError('{0} is not readable by the current user.'.format(self.cacert))

    def connect(self, address, family, proto, use_ssl=False):
        '''Returns a socket for a given addres, family and protocol.'''

        sock = socket.socket(family, proto)

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if 'host' in address and 'port' in address:
            addr = (address['host'], address['port'])
        elif 'filename' in address:
            addr = address['filename']
        else:
            raise ServerStartupError("Address {0} is not a proper LogHog address.".format(address))
        sock.bind((addr))

        if proto == socket.SOCK_STREAM:
            sock.listen(self.STREAM_SOCKET_BACKLOG)
        
        self.log.info(format_connection_message(address, family, proto, use_ssl))

        return sock

    def run(self):
        '''Runs the main loop, collecting data and sending it to the callback.'''

        while True:
            try:
                if self.select_timeout:
                    r, w, _ = select.select(self.all_socks, [], [], self.select_timeout)
                else:
                    r, w, _ = select.select(self.all_socks, [], [])
            except Exception as exc:
                if isinstance(exc, select.error) and exc.args[0] == 4:
                    continue # Got signal, probably HUP
                else:
                    raise

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
                        self.connect_client_stream(clientsock, addr, use_ssl=(sock in self.ssl_socks))
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

            if self.closed:
                self.close()
                break

    def connect_client_stream(self, sock, addr, use_ssl):
        '''Adds a new socket to the list of stream sockets.'''

        try:
            if use_ssl:
                sock = ssl.wrap_socket(sock,
                    keyfile=self.pemfile,
                    certfile=self.pemfile,
                    ca_certs=self.cacert,
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

        size, flags = struct.unpack(self.HEADER_FORMAT, buf[:self.HEADER_SIZE])
        if len(buf) >= self.HEADER_SIZE + size:
            payload = struct.unpack(self.MSG_FORMAT_PROTO % size, buf[self.HEADER_SIZE:size+self.HEADER_SIZE])[0]
            buf = buf[self.HEADER_SIZE + size:]

            if flags & self._FLAGS_GZIP:
                payload = zlib.decompress(payload)

            return payload, buf
        else:
            return None, None

    def close(self):
        for sock in self.client_stream_socks:
            sock.shutdown(socket.SHUT_RDWR)

        if self.client_stream_socks:
            time.sleep(self.SHUTDOWN_TIMEOUT)

        for sock in self.all_socks:
            sock.close()

    def shutdown(self):
        '''Notifies the server of a shutdown condition.'''

        self.closed = True
        self.select_timeout = self.SHUTDOWN_TIMEOUT


