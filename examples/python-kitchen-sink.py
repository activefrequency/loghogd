#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

curdir = os.path.abspath(os.path.dirname(__file__))
sys.path = [os.path.join(os.path.dirname(curdir), 'clients')] + sys.path

import logging, time
from loghog import LoghogHandler

def setup_logging():
    logger = logging.getLogger()

    ssl_info = {
        'pemfile': os.path.join(curdir, 'conf', 'certs', 'test-client.pem'),
        'cacert': os.path.join(curdir, 'conf', 'certs', 'loghog-ca.cert'),
    }

    handler = LoghogHandler('kitchen-sink-app',
        address=('localhost', 5577),# Default is ('localhost', 5566). Port 5577 is usually SSL enabled
        stream=True,                # Default is True
        secret='my-big-secret',     # Specify this if the server expects it
        compression=True,           # Default is False
        hostname='example01',       # Default is determined automatiaclly
        ssl_info=ssl_info,          # Default is None for disabled SSL
        print_debug=True            # Default is False. Prints connection errors to STDOUT
    )

    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


setup_logging()

log = logging.getLogger()

while True:
    log.info(u"That is one hot jalapño!")
    time.sleep(1)
