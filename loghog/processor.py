
import hmac, logging
try:
    import json
except ImportError:
    import simplejson as json

class LogParseError(Exception):

    def __init__(self, desc, data):
        super(Exception, self).__init__(self, desc)
        self.data = data

class Processor(object):
    REQUIRED_FIELDS = ['version', 'stamp', 'nsecs', 'app_id', 'module', 'body', ]
    HASHABLE_FIELDS = ['app_id', 'module', 'stamp', 'body']

    def __init__(self, facility_db, writer):
        self.facility_db = facility_db
        self.writer = writer

        self.log = logging.getLogger()

    def validate_msg(self, msg):
        for field in self.REQUIRED_FIELDS:
            if field not in msg:
                raise LogParseError('Invalid message: "%s" is not in the message' % field, msg)

    def verify_signature(self, facility, msg):
        if facility.secret:
            if 'signature' not in msg:
                raise LogParseError('Security alert: message signature is required but not present', msg)

            hashable = ''.join(x for x in self.HASHABLE_FIELDS)
            signature = hmac.new(facility.secret, hashable).hexdigest()

            if signature != msg['signature']:
                raise LogParseError('Security alert: message signature is invalid', msg)

    def parse_message(self, data):
        try:
            msg = json.loads(data)
        except ValueError, e:
            raise LogParseError('Message payload is not valid JSON: %s' % e, data)

        self.validate_msg(msg)

        return msg

    def on_message(self, msg_bytes, addr):
        try:
            msg = self.parse_message(msg_bytes)

            facility = self.facility_db.get_facility(msg['app_id'], msg['module'])
            if not facility:
                return # XXX: should we raise?
            
            self.verify_signature(facility, msg)

            self.log.debug(repr(msg))
            self.writer.write(facility.app_id, facility.mod_id, msg)
        except Exception, e:
            self.log.error('An error occured processing message: %s', msg_bytes)
            self.log.exception(e)

