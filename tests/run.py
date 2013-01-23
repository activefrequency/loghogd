
import sys, os, unittest

curdir = os.path.abspath(os.path.dirname(__file__))
src = os.path.join(os.path.dirname(curdir), 'loghogd')

sys.path = [src] + sys.path

suites = []

for _, _, files in os.walk(curdir):
    for filename in files:
        if filename.endswith('_test.py'):
            testmodule = __import__(filename[:-3])
            suites += unittest.defaultTestLoader.loadTestsFromModule(testmodule)

for suite in suites:
    unittest.TextTestRunner(verbosity=2).run(suite)

