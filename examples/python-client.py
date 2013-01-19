#!/usr/bin/env python

import sys, os

curdir = os.path.dirname(__file__)
sys.path = [os.path.join(os.path.dirname(curdir), 'clients')] + sys.path

import logging, time
from loghog import LoghogHandler

def setup_logging():
    logger = logging.getLogger()

    ssl_info = {
        'pemfile': os.path.join(curdir, 'certs', 'test-client.pem'),
        'cafile': os.path.join(curdir, 'certs', 'loghog-ca.cert'),
    }

    handler = LoghogHandler('proga', address=('localhost', 5566), mode=LoghogHandler.STREAM, secret='qqq1', compression=LoghogHandler.USE_GZIP, ssl_info=ssl_info)
    formatter = logging.Formatter('%(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)


setup_logging()

log = logging.getLogger('web1.qqq')

while True:
    log.info(u"hello world!")
    #log.info('\xe8\xaf\xb7\xe6\x94\xb6\xe8\x97\x8f\xe6\x88\x91\xe4\xbb\xac\xe7\x9a\x84\xe7\xbd\x91\xe5\x9d\x80')
    time.sleep(1)
