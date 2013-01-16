
import unittest, os
from facilities import FacilityDB, FacilityError, pretty_mod_id, parse_mod_id

class FacilitiesTest(unittest.TestCase):
 
    def setUp(self):
        self.db = FacilityDB()

        self.db.load_config(os.path.join(os.path.dirname(__file__), 'data', 'facilities.conf'))

    def test_parse_mod_id_1(self):
        mod_id = parse_mod_id('web')
        self.assertEqual(('root', 'web'), mod_id)

    def test_parse_mod_id_2(self):
        mod_id = parse_mod_id('web.foo')
        self.assertEqual(('root', 'web', 'foo'), mod_id)

    def test_parse_mod_id_3(self):
        mod_id = parse_mod_id('')
        self.assertEqual(('root', ), mod_id)

    def test_parse_mod_id_4(self):
        mod_id = parse_mod_id('root')
        self.assertEqual(('root', ), mod_id)

    def test_pretty_mod_id_1(self):
        mod_id = pretty_mod_id(('root', 'web'))
        self.assertEqual('web', mod_id)

    def test_pretty_mod_id_2(self):
        mod_id = pretty_mod_id(('root', 'web', 'foo'))
        self.assertEqual('web.foo', mod_id)

    def test_pretty_mod_id_3(self):
        mod_id = pretty_mod_id(('root',))
        self.assertEqual('root', mod_id)

    def test_mod_id_identity_1(self):
        self.assertEqual('root', pretty_mod_id(parse_mod_id('root')))
        
    def test_mod_id_identity_2(self):
        self.assertEqual('web', pretty_mod_id(parse_mod_id('root.web')))
        
    def test_mod_id_identity_3(self):
        self.assertEqual('web.foo', pretty_mod_id(parse_mod_id('root.web.foo')))
        
    def test_mod_id_identity_4(self):
        self.assertEqual(('root', ), parse_mod_id(pretty_mod_id(('root', ))))
        
    def test_mod_id_identity_5(self):
        self.assertEqual(('root', 'web'), parse_mod_id(pretty_mod_id(('root', 'web'))))
        
    def test_mod_id_identity_6(self):
        self.assertEqual(('root', 'web', 'foo'), parse_mod_id(pretty_mod_id(('root', 'web', 'foo'))))
        
    def test_facility_search_1(self):
        f = self.db.get_facility('app-name', '')
        self.assertEqual((f.app_id, f.mod_id), ('app-name', ('root', )))

    def test_facility_search_2(self):
        f = self.db.get_facility('app-name', 'web')
        self.assertEqual((f.app_id, f.mod_id), ('app-name', ('root', 'web', )))

    def test_facility_search_3(self):
        f = self.db.get_facility('app-name', 'web.errors')
        self.assertEqual((f.app_id, f.mod_id), ('app-name', ('root', 'web', 'errors', )))

    def test_facility_search_4(self):
        f = self.db.get_facility('app-name', 'web.does-not-exist')
        self.assertEqual((f.app_id, f.mod_id), ('app-name', ('root', 'web', )))

    def test_facility_search_5(self):
        f = self.db.get_facility('app-name', 'does-not-exist')
        self.assertEqual((f.app_id, f.mod_id), ('app-name', ('root', )))

    def test_facility_search_6(self):
        f = self.db.get_facility('no-such-app', '')
        self.assertEqual(f, None)

    def test_no_root_config(self):
        filename = os.path.join(os.path.dirname(__file__), 'data', 'facilities-with-no-root.conf')
        self.assertRaises(FacilityError, self.db.load_config, filename)

