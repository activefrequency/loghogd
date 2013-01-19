
from __future__ import print_function
import socket, hmac, hashlib, struct, zlib, ssl, random
import logging, logging.handlers

try:
    import json
except ImportError:
    import simplejson as json

class LoghogHandler(logging.handlers.SocketHandler):

    VERSION = 1

    _FLAGS_GZIP = 0x01

    FORMAT_PROTO = '!LL %ds'

    HMAC_DIGEST_ALGO = hashlib.md5

    def __init__(self, app_name, address=('localhost', 5566), stream=True, secret=None, compression=False, hostname=None, ssl_info=None, print_debug=False):
        '''Initializes the LoghogHandler instance.

        param app_name : basestring
            Name of your app. This should be listed in loghogd.conf
        param address : 2-tuple
            (ip_address, port) of the server
        param stream : bool
            Whether to use a stream or a datagram protocol
        param secret : bytestring
            Hashable secret shared with the server. Used for message signing
        param hostname : str
            Local hostname. If not bool(hostname) it is determined automatically
        param ssl_info : dict
            A dictionary containing two keys: pemfile and cacert. These should be paths to the
            SSL certificates necessary to talk to the server
        param print_debug : bool
            This argument controls whether errors are suppressed silently, or printed to stdout.
            Use this if you are using SSL to view connection errors.
        '''

        logging.Handler.__init__(self)

        self.app_name = app_name
        self.address = address
        self.use_stream = stream
        self.secret = secret
        self.compression = compression 
        self.hostname = hostname
        self.compression = None
        self.print_debug = print_debug

        self.pemfile = None
        self.cacert = None

        if ssl_info:
            self.pemfile = ssl_info['pemfile']
            self.cacert = ssl_info['cacert']

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

    def _resolve_addr(self, address, use_stream):
        '''Resolves the given address and mode into a randomized address record.'''

        socktype = socket.SOCK_STREAM if use_stream else socket.SOCK_DGRAM
        res = socket.getaddrinfo(address[0], address[1], 0, socktype)
        random.shuffle(res)
        return res[0]

    def makeSocket(self, timeout=1.0):
        '''Makes a connection to the socket.'''

        af, socktype, proto, cannonname, sa = self._resolve_addr(self.address, self.use_stream)
        
        s = socket.socket(af, socktype, proto)

        if hasattr(s, 'settimeout'):
            s.settimeout(timeout)

        if self.use_stream and self.pemfile:
            s = ssl.wrap_socket(s,
                keyfile=self.pemfile,
                certfile=self.pemfile,
                ca_certs=self.cacert,
                server_side=False,
                cert_reqs=ssl.CERT_REQUIRED
            )

            try:
                s.connect(sa)
            except Exception as e:
                if self.print_debug:
                    print(e)

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

        if self.compression:
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
            if self.use_stream:
                self.sock.sendall(s)
            else:
                self.sock.sendto(s, self.address)
        except socket.error:
            self.close()

