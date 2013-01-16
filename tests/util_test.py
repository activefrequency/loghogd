
import unittest
from util import parse_addrs

class UtilTest(unittest.TestCase):
    
    def test_parse_addr_ipv4_def_port(self):
        res = tuple(parse_addrs('127.0.0.1', 8888))
        self.assertEqual(res, (('127.0.0.1', 8888),))

    def test_parse_addr_ipv4_custom_port(self):
        res = tuple(parse_addrs('127.0.0.1:8888', 8888))
        self.assertEqual(res, (('127.0.0.1', 8888),))

    def test_parse_addr_ipv6_def_port(self):
        res = tuple(parse_addrs('[::1]', 8888))
        self.assertEqual(res, (('::1', 8888),))

    def test_parse_addr_ipv6_custom_port(self):
        res = tuple(parse_addrs('[::1]:8888', 8888))
        self.assertEqual(res, (('::1', 8888),))

    def test_parse_addr_ipv6_def_port_multiple(self):
        res = tuple(parse_addrs('[::1],[::2]', 8888))
        self.assertEqual(res, (('::1', 8888), ('::2', 8888),))

    def test_parse_addr_ipv6_custom_port_multiple(self):
        res = tuple(parse_addrs('[::1]:8888,[::2]:9999,[::3]', 8888))
        self.assertEqual(res, (('::1', 8888), ('::2', 9999), ('::3', 8888)))

