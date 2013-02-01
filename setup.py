#!/usr/bin/env python

from setuptools import setup, find_packages

from loghogd import __version__ as VERSION

setup(
    name = 'loghogd',
    version = VERSION,
    description = 'Modern log storage server',
    author = 'Active Frequency',
    author_email = 'info@activefrequency.com',
    url = 'https://github.com/activefrequency/loghogd',
    license = 'Apache2',
    test_suite = 'tests.tests_all',
    packages = find_packages(exclude=['ez_setup', 'examples', 'tests']),
    scripts = ['bin/loghogd', 'bin/loghog-server-cert', 'bin/loghog-client-cert'],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache2 License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
    ],
)
