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

    handler = LoghogHandler('my-first-app', address=('localhost', 5577), ssl_info=ssl_info, print_debug=True)

    handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


setup_logging()

log = logging.getLogger()

while True:
    log.info(u"That is one hot jalapño!")
    time.sleep(1)
