
from __future__ import print_function
import sys, os, unittest, subprocess, errno

curdir = os.path.abspath(os.path.dirname(__file__))
src = os.path.join(os.path.dirname(curdir), 'loghogd')

sys.path = [src] + sys.path

suites = []

suffixes = ['_test.py']

if len(sys.argv) > 1 and sys.argv[1].strip() == '--all':
    try:
        devnull = open(os.devnull, 'wb')
        subprocess.call('vagrant', stdout=devnull, stderr=devnull)
    except OSError as e:
        if e.errno == errno.ENOENT:
            print('ERROR: You requested build tests to be run, but vagrant is not installed!')
            print('Install vagrant and try again. Alternatively, omit the --all option.')
            print()
            sys.exit(os.EX_UNAVAILABLE)
        else:
            raise
    finally:
        devnull.close()

    print('Running all tests, including long-running build tests.')
    print('The build tests may take a VERY long time and use significat')
    print('system resources, such as disk space, bandwidth, RAM, and CPU.')
    print('Expect the first run of these test to take up to an hour.')
    print()
    print('After the first run of the build tests, several virtual machine')
    print('images will be downloaded to your home directory.')
    print()

    suffixes.append('_bigtest.py')

for _, _, files in os.walk(curdir):
    for filename in files:
        for suf in suffixes:
            if filename.endswith(suf):
                testmodule = __import__(filename[:-3])
                suites += unittest.defaultTestLoader.loadTestsFromModule(testmodule)
                break

for suite in suites:
    unittest.TextTestRunner(verbosity=2).run(suite)

