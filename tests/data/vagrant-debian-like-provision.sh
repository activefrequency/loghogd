#!/bin/sh

set -u
set -e

DEBIAN_FRONTEND=noninteractive apt-get update -qq > /dev/null
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends -qq git-core build-essential fakeroot devscripts debhelper python-setuptools python-all python-support python-dateutil > /dev/null

cd loghogd

debuild -us -uc -I'.git'

cd ..

dpkg -i loghogd*_all.deb

/etc/init.d/loghogd status
/etc/init.d/loghogd stop
/etc/init.d/loghogd start
/etc/init.d/loghogd restart
/etc/init.d/loghogd reload
/etc/init.d/loghogd status

exit 0
