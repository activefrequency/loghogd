
import socket, hmac, hashlib, struct, zlib, ssl, random
import logging, logging.handlers

try:
    import json
except ImportError:
    import simplejson as json

class LoghogHandler(logging.handlers.SocketHandler):

    VERSION = 1
    DGRAM = 0x01
    STREAM = 0x02

    USE_GZIP = 0x01

    _FLAGS_GZIP = 0x01

    FORMAT_PROTO = '!LL %ds'

    HMAC_DIGEST_ALGO = hashlib.md5

    def __init__(self, app_name, address=('localhost', 5566), mode=STREAM, secret=None, compression=None, hostname=None, ssl_info=None):
        logging.Handler.__init__(self)

        self.app_name = app_name
        self.address = address
        self.mode = mode
        self.secret = secret
        self.compression = compression 
        self.hostname = hostname
        self.compression = None

        self.keyfile = None
        self.certfile = None
        self.cafile = None

        if ssl_info:
            self.keyfile = ssl_info['keyfile']
            self.certfile = ssl_info['certfile']
            self.cafile = ssl_info['cafile']

        if not hostname:
            self.hostname = socket.gethostname()

        self.flags = 0
        if self.compression:
            self.flags |= self._FLAGS_GZIP

        self.sock = None
        self.closeOnError = 0
        self.retryTime = None
        #
        # Exponential backoff parameters.
        #
        self.retryStart = 1.0
        self.retryMax = 30.0
        self.retryFactor = 2.0

    def _resolve_addr(self, address, mode):
        '''Resolves the given address and mode into a randomized address record.'''

        socktype = socket.SOCK_DGRAM if mode == self.DGRAM else socket.SOCK_STREAM
        res = socket.getaddrinfo(address[0], address[1], 0, socktype)
        random.shuffle(res)
        return res[0]

    def makeSocket(self, timeout=1.0):
        '''Makes a connection to the socket.'''

        af, socktype, proto, cannonname, sa = self._resolve_addr(self.address, self.mode)
        
        s = socket.socket(af, socktype, proto)

        if hasattr(s, 'settimeout'):
            s.settimeout(timeout)

        if self.mode == self.STREAM:
            if self.keyfile:
                s = ssl.wrap_socket(s,
                    keyfile=self.keyfile,
                    certfile=self.certfile,
                    server_side=False,
                    cert_reqs=ssl.CERT_NONE, # XXX should be ssl.CERT_REQUIRED
                    ca_certs=self.cafile,
                    ssl_version=ssl.PROTOCOL_TLSv1,
                    do_handshake_on_connect=True,
                    suppress_ragged_eofs=True,
                    ciphers=None
                )

            try:
                s.connect(sa)
            except Exception:
                pass

        return s

    def _encode(self, record):
        '''Encodes a log record into the loghog on-wire protocol.'''

        data = {
            'version': self.VERSION,
            'app_id': self.app_name,
            'module': record.name,
            'stamp': int(record.created),
            'nsecs': int(record.msecs * 10**6),
            'hostname': self.hostname,
            'body': self.format(record),
        }

        if self.secret:
            hashable_fields = ['app_id', 'module', 'stamp', 'nsecs', 'body']
            hashable = u''.join(unicode(data[field]) for field in hashable_fields).encode('utf-8')
            data['signature'] = hmac.new(self.secret, hashable, self.HMAC_DIGEST_ALGO).hexdigest()

        payload = json.dumps(data)

        if self.compression == self.USE_GZIP:
            payload = zlib.compress(payload)

        size = len(payload)
        return struct.pack(self.FORMAT_PROTO % size, size, self.flags, payload)

    def emit(self, record):
        '''Encodes and sends the messge over the network.'''

        self.send(self._encode(record))

    def send(self, s):
        '''Attempts to create a network connection and send the data.'''

        if self.sock is None:
            self.createSocket()

        if not self.sock:
            return

        try:
            if self.mode == self.DGRAM:
                self.sock.sendto(s, self.address)
            elif self.mode == self.STREAM:
                self.sock.sendall(s)
        except socket.error:
            self.close()

