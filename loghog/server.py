import socket, os, select, struct, zlib, errno, ssl

class Server(object):
    STREAM_SOCKET_BACKLOG = 5
    MAX_MSG_SIZE = 1024*8

    BUFSIZE = 4096
    _FLAGS_GZIP = 0x01
    
    HEADER_FORMAT = '!LL'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MSG_FORMAT_PROTO = '%ds'

    def __init__(self, callback, ipv4_addrs=tuple(), ipv6_addrs=tuple(), unix_sockets=tuple(), keyfile=None, certfile=None, cafile=None):
        self.callback = callback
        self.closed = False

        self.keyfile = keyfile
        self.certfile = certfile
        self.cafile = cafile

        self.stream_socks = set()
        self.dgram_socks = set()
        self.unix_sockets = set()

        self.client_stream_socks = set()
        self.stream_buffers = {}

        for addr in ipv4_addrs:
            self.stream_socks.add(self.connect(addr, socket.AF_INET, socket.SOCK_STREAM))
            self.dgram_socks.add(self.connect(addr, socket.AF_INET, socket.SOCK_DGRAM))

        for addr in ipv6_addrs:
            self.stream_socks.add(self.connect(addr, socket.AF_INET6, socket.SOCK_STREAM))
            self.dgram_socks.add(self.connect(addr, socket.AF_INET6, socket.SOCK_DGRAM))

        for addr in unix_sockets:
            stream_addr = '%s.%s' % (addr, 'stream')
            dgram_addr = '%s.%s' % (addr, 'dgram')
            
            self.unlink_unix_sock(stream_addr)
            self.unlink_unix_sock(dgram_addr)

            self.unix_sockets.add(stream_addr)
            self.unix_sockets.add(dgram_addr)
            
            self.stream_socks.add(self.connect(stream_addr, socket.AF_UNIX, socket.SOCK_STREAM))
            self.dgram_socks.add(self.connect(dgram_addr, socket.AF_UNIX, socket.SOCK_DGRAM))

        self.all_socks = set(self.stream_socks | self.dgram_socks)

    def unlink_unix_sock(self, filename):
        '''Removes the UNIX socket file if it exists.'''

        try:
            os.unlink(filename)
        except OSError as e:
            if e.errno == errno.ENOENT: # File does not exist
                pass
            else:
                raise

    def connect(self, address, family, proto):
        '''Returns a socket for a given addres, family and protocol.'''

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
                    self.connect_client_stream(clientsock)

                elif sock in self.client_stream_socks:
                    # Read client data
                    data = sock.read(self.BUFSIZE) if isinstance(sock, ssl.SSLSocket) else sock.recv(self.BUFSIZE)
                    if data:
                        self.stream_buffers[sock].append(data)
                    
                    for msg, addr in self.parse_stream_buffer(sock):
                        self.callback(msg, addr)

                    if not data:
                        self.disconnect_client_stream(sock)

    def connect_client_stream(self, sock):
        '''Adds a new socket to the list of stream sockets.'''

        if self.keyfile:
            sock = ssl.wrap_socket(sock,
                keyfile=self.keyfile,
                certfile=self.certfile,
                server_side=True,
                cert_reqs=ssl.CERT_NONE, # XXX should be ssl.CERT_REQUIRED
                ca_certs=self.cafile,
                ssl_version=ssl.PROTOCOL_TLSv1,
                do_handshake_on_connect=True,
                suppress_ragged_eofs=True,
                ciphers=None
            )

        self.client_stream_socks.add(sock)
        self.all_socks.add(sock)
        self.stream_buffers[sock] = []

    def disconnect_client_stream(self, sock):
        '''Removes all references to a client stream.'''

        self.client_stream_socks.remove(sock)
        self.all_socks.remove(sock)
        del self.stream_buffers[sock]
        sock.close()

    def parse_stream_buffer(self, sock):
        '''Parses all the complete packets from the buffer and returns a generator.'''

        buf = ''.join(self.stream_buffers[sock])
        if len(buf) < self.HEADER_SIZE:
            return

        while True:
            if len(buf) > self.HEADER_SIZE:
                payload, buf = self.parse_datagram(buf)
                if payload:
                    yield payload, None # XXX: Do not return None
                else:
                    break
            else:
                break

        self.stream_buffers[sock] = [] if not buf else [buf]

    def parse_datagram(self, buf):
        size, flags = struct.unpack(self.HEADER_FORMAT, buf[:self.HEADER_SIZE])
        if len(buf) >= self.HEADER_SIZE + size:
            payload, = struct.unpack(self.MSG_FORMAT_PROTO % size, buf[self.HEADER_SIZE:])
            buf = buf[self.HEADER_SIZE + size:]

            if flags & self._FLAGS_GZIP:
                payload = zlib.decompress(payload)

            return payload, buf
        else:
            return None, None

    def close(self):
        '''Closes all open server sockets and removes UNIX socket files.'''

        for sock in self.all_socks:
            family = sock.family
            name = sock.getsockname()
            
            sock.close()
            
            if family == socket.AF_UNIX:
                self.unlink_unix_sock(name)

        self.closed = True

