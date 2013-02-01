# -*- coding: utf-8 -*-

import unittest, hmac
from processor import Processor, LogParseError
try:
    import json
except ImportError:
    import simplejson as json

class FacilitiesTest(unittest.TestCase):
 
    def setUp(self):
        self.processor = Processor(None, None)

    def test_verify_signature_1(self):
        msg = {
            'app_id': 'app-name',
            'module': 'web.foo',
            'stamp': 1358363502,
            'nsecs': 12043,
            'body': u'If numbers aren’t beautiful, I don’t know what is. –Paul Erdős',
        }
        
        secret = '01WzaGPu'

        hashable = u''.join(unicode(msg[field]) for field in self.processor.HASHABLE_FIELDS).encode('utf-8')
        msg['signature'] = hmac.new(secret, hashable).hexdigest()

        try:
            self.processor.verify_signature(secret, msg)
        except LogParseError as e:
            self.assertTrue(False, 'verify_signature() raised an error: {0}'.format(e))

    def test_verify_signature_2(self):
        msg = {
            'app_id': 'app-name',
            'module': 'web.foo',
            'stamp': 1358363502,
            'nsecs': 12043,
            'body': u'If numbers aren’t beautiful, I don’t know what is. –Paul Erdős',
        }
        
        secret = '01WzaGPu'

        hashable = u''.join(unicode(msg[field]) for field in self.processor.HASHABLE_FIELDS).encode('utf-8')
        msg['signature'] = hmac.new(secret, hashable).hexdigest()

        self.assertRaises(LogParseError, self.processor.verify_signature, secret + ' some junk', msg)

    def test_verify_signature_3(self):
        msg = {
            'app_id': 'app-name',
            'module': 'web.foo',
            'stamp': 1358363502,
            'nsecs': 12043,
            'body': u'If numbers aren’t beautiful, I don’t know what is. –Paul Erdős',
        }
        
        secret = None

        try:
            self.processor.verify_signature(secret, msg)
        except LogParseError as e:
            self.assertTrue(False, 'verify_signature() raised an error: {0}'.format(e))

    def test_parse_message_1(self):
        msg = {
            'app_id': 'app-name',
            'module': 'web.foo',
            'stamp': 1358363502,
            'nsecs': 12043,
            'body': u'If numbers aren’t beautiful, I don’t know what is. –Paul Erdős',
            'version': 1,
            'hostname': 'example.com',
        }
        
        secret = '01WzaGPu'
        hashable = u''.join(unicode(msg[field]) for field in self.processor.HASHABLE_FIELDS).encode('utf-8')
        msg['signature'] = hmac.new(secret, hashable).hexdigest()


        msg_str = json.dumps(msg)
        try:
            parsed = self.processor.parse_message(msg_str)
        except LogParseError as e:
            self.assertTrue(False, 'parse_message() raised an error: {0}'.format(e))

        for key, val in msg.iteritems():
            self.assertEqual(val, parsed[key])

    def test_parse_message_2(self):
        msg = {
            #'app_id': 'app-name', # Will be missing
            'module': 'web.foo',
            'stamp': 1358363502,
            'nsecs': 12043,
            'body': u'If numbers aren’t beautiful, I don’t know what is. –Paul Erdős',
            'version': 1,
            'hostname': 'example.com',
        }
        
        msg_str = json.dumps(msg)
        self.assertRaises(LogParseError, self.processor.parse_message, msg_str)
