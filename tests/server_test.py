# -*- coding: utf-8 -*-

import unittest, struct, zlib
from server import Server

class ServerTest(unittest.TestCase):
    
    FORMAT_PROTO = '!LL %ds'
 
    def setUp(self):
        self.server = Server(None, conf_root='', listen_ipv4='', listen_ipv6='', listen_ipv4_ssl='', listen_ipv6_ssl='', default_port=0, default_port_ssl=0, pemfile='', cacert='')

    def test_parse_datagram_1(self):
        payload = u"That is one hot jalapño!".encode('utf-8')
        size = len(payload)

        buf = struct.pack(self.FORMAT_PROTO % size, size, 0, payload)

        res_payload, buf = self.server.parse_datagram(buf)

        self.assertEqual(payload, res_payload)

    def test_parse_datagram_2(self):
        payload = u"That is one hot jalapño!".encode('utf-8')
        size = len(payload)

        buf = struct.pack(self.FORMAT_PROTO % size, size + 1, 0, payload)

        res_payload, buf = self.server.parse_datagram(buf)

        self.assertEqual(None, res_payload)

    def test_parse_datagram_3(self):
        orig_payload = u"That is one hot jalapño!".encode('utf-8')
        payload = zlib.compress(orig_payload)
        
        size = len(payload)

        buf = struct.pack(self.FORMAT_PROTO % size, size, 0x01, payload)

        res_payload, buf = self.server.parse_datagram(buf)

        self.assertEqual(orig_payload, res_payload)

