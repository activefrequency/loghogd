
import socket, hmac, struct, zlib, ssl
import logging, logging.handlers

import time

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

    def __init__(self, address, service_name, mode=DGRAM, secret=None, compression=None, hostname=None, ssl_info=None):
        logging.Handler.__init__(self)

        self.service_name = service_name
        self.address = address
        self.mode = mode
        self.secret = secret
        self.compression = compression
        self.hostname = hostname

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

    def makeSocket(self, timeout=1.0):
        proto = socket.SOCK_DGRAM if self.mode == self.DGRAM else socket.SOCK_STREAM
        s = socket.socket(socket.AF_INET, proto)

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
                s.connect(self.address)
            except Exception:
                pass

        return s

    def _encode(self, record):
        data = {
            'version': self.VERSION,
            'app_id': self.service_name,
            'module': record.name,
            'stamp': int(record.created),
            'nsecs': int(record.msecs * 10**6),
            'hostname': self.hostname,
            'body': self.format(record),
        }

        if self.secret:
            hashable_fields = ['app_id', 'module', 'stamp', 'body']
            hashable = ''.join(x for x in hashable_fields)
            data['signature'] = hmac.new(self.secret, hashable).hexdigest()

        payload = json.dumps(data)

        if self.compression == self.USE_GZIP:
            payload = zlib.compress(payload)

        size = len(payload)
        return struct.pack(self.FORMAT_PROTO % size, size, self.flags, payload)

    def emit(self, record):
        encoded = self._encode(record)
        size, headers = struct.unpack('!LL', encoded[:struct.calcsize('!LL')])
        self.send(self._encode(record))

    def send(self, s):
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


def setup_logging():
    logger = logging.getLogger()

    ssl_info = {
        'keyfile': 'thestral.local.key',
        'certfile': 'thestral.local.crt',
        'cafile': None,
    }

    handler = LoghogHandler(address=('localhost', 8888), mode=LoghogHandler.STREAM, service_name='proga', secret='qqq1', compression=LoghogHandler.USE_GZIP, ssl_info=ssl_info)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


setup_logging()

log = logging.getLogger('web1.qqq')

while True:
    log.info(u"hello world!")
    #log.info('\xe8\xaf\xb7\xe6\x94\xb6\xe8\x97\x8f\xe6\x88\x91\xe4\xbb\xac\xe7\x9a\x84\xe7\xbd\x91\xe5\x9d\x80')
    time.sleep(1)


def foo():
    bar()

def bar():
    raise Exception('eeeeeeee')

try:
    #foo()
    pass
except Exception as e:
    log.exception(e)

