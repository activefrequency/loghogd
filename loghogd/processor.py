
import hmac, hashlib, logging
from util import pretty_addr
try:
    import json
except ImportError:
    import simplejson as json

class LogParseError(Exception):
    '''Error raised when a message payload cannot be parsed.'''

    def __init__(self, desc, data):
        super(Exception, self).__init__(self, desc)
        self.data = data

class Processor(object):
    '''Class responsible for parsing messages and dispatching them to the Writer.'''

    REQUIRED_FIELDS = ['version', 'stamp', 'nsecs', 'app_id', 'module', 'body', ]
    HASHABLE_FIELDS = ['app_id', 'module', 'stamp', 'nsecs', 'body']

    HMAC_DIGEST_ALGO = hashlib.md5

    def __init__(self, facility_db, writer):
        '''Initializes the Processor instance with the given facility_db and writer instances.'''

        self.facility_db = facility_db
        self.writer = writer

        self.log = logging.getLogger()

    def validate_msg(self, msg):
        '''Validates that the given message has all the required fields.'''

        for field in self.REQUIRED_FIELDS:
            if field not in msg:
                raise LogParseError('Invalid message: "%s" is not in the message' % field, msg)

    def verify_signature(self, secret, msg):
        '''Validates message signature agains the shared secret.

        secret must be a string or None.'''

        if secret:
            if 'signature' not in msg:
                raise LogParseError('Security alert: message signature is required but not present', msg)

            hashable = u''.join(unicode(msg[field]) for field in self.HASHABLE_FIELDS).encode('utf-8')
            signature = hmac.new(secret, hashable, self.HMAC_DIGEST_ALGO).hexdigest()

            if signature != msg['signature']:
                raise LogParseError('Security alert: message signature is invalid', msg)

    def parse_message(self, data):
        '''Parses the message payload into a validated dict() instance.'''

        try:
            msg = json.loads(data)
        except ValueError as e:
            raise LogParseError('Message payload is not valid JSON: %s' % e, data)

        self.validate_msg(msg)

        return msg

    def on_message(self, msg_bytes, addr):
        '''Callback method called by Server when new messages arrive.'''

        try:
            msg = self.parse_message(msg_bytes)

            facility = self.facility_db.get_facility(msg['app_id'], msg['module'])
            if not facility:
                self.log.warning("Recevied message for app {0}, but could not find corresponding facility.".format(msg['app_id']))
                return

            try:
                self.verify_signature(facility.secret, msg)
            except LogParseError as e:
                self.log.warning('Signature verification error: {0}'.format(e))

            self.log.debug('Got message %r from %r', msg, pretty_addr(addr))
            self.writer.write(facility.app_id, facility.mod_id, msg)
        except Exception as e:
            self.log.error('An error occured processing message: {0}'.format(msg_bytes))
            self.log.exception(e)

