#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os

curdir = os.path.dirname(__file__)
sys.path = [os.path.join(os.path.dirname(curdir), 'clients')] + sys.path

import logging, time
from loghog import LoghogHandler

def setup_logging():
    logger = logging.getLogger()

    ssl_info = {
        'pemfile': os.path.join(curdir, 'certs', 'test-client.pem'),
        'cacert': os.path.join(curdir, 'certs', 'loghog-ca.cert'),
    }

    handler = LoghogHandler('proga', address=('localhost', 5566), secret='qqq1', compression=True, ssl_info=ssl_info, print_debug=True)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


setup_logging()

log = logging.getLogger('web1.qqq')

while True:
    log.info(u"That is one hot jalapño!")
    time.sleep(1)
