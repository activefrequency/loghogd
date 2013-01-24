
import unittest, os
from subprocess import Popen, PIPE

class BuildTest(unittest.TestCase):
 
    def call(self, command, cwd):
        '''A wrapper around Popen. Returns (status, stdout, stderr).'''

        p = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, cwd=cwd)
        out, err = p.communicate()
        return (p.returncode, out, err)

    def format_error(self, status, out, err):
        error = [
            'An error occured while performing external command.'
            'stdout was:',
            out,
            'stderr was:',
            err,
            'status was:',
            str(status),
            '\n\n',
        ]

        return '\n\n'.join(error)

    def setUp(self):
        self.curdir = os.path.dirname(os.path.abspath(__file__))
        self.datadir = os.path.join(self.curdir, 'data')

    def tearDown(self):
        status, out, err = self.call('vagrant destroy -f {0}'.format(self.box_name), cwd=self.datadir)
        self.assertEqual(status, 0, self.format_error(status, out, err))

    def test_ubuntu_precise(self):
        self.box_name = 'precise'

        status, out, err = self.call('vagrant up {0}'.format(self.box_name), cwd=self.datadir)
    
        self.assertEqual(status, 0, self.format_error(status, out, err))

    def test_ubuntu_lucid(self):
        self.box_name = 'lucid'

        status, out, err = self.call('vagrant up {0}'.format(self.box_name), cwd=self.datadir)
    
        self.assertEqual(status, 0, self.format_error(status, out, err))

    def test_ubuntu_quantal(self):
        self.box_name = 'quantal'

        status, out, err = self.call('vagrant up {0}'.format(self.box_name), cwd=self.datadir)
    
        self.assertEqual(status, 0, self.format_error(status, out, err))

    def test_debain_squeeze(self):
        self.box_name = 'squeeze'

        status, out, err = self.call('vagrant up {0}'.format(self.box_name), cwd=self.datadir)
    
        self.assertEqual(status, 0, self.format_error(status, out, err))

    def test_debain_wheezy(self):
        self.box_name = 'wheezy'

        status, out, err = self.call('vagrant up {0}'.format(self.box_name), cwd=self.datadir)
    
        self.assertEqual(status, 0, self.format_error(status, out, err))

