#!/usr/bin/env python

from setuptools import setup

from loghog import __version__ as VERSION

setup(
    name = 'loghog',
    version = VERSION,
    description = 'Modern log storage server',
    author = 'Active Frequency',
    author_email = 'info@activefrequency.com',
    url = 'https://github.com/activefrequency/loghog',
    license = 'Apache2',
    py_modules = ['loghog'],
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
