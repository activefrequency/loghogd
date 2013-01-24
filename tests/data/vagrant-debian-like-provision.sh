#!/bin/sh

set -u
set -e

GIT_REPO=git://github.com/activefrequency/loghogd.git

DEBIAN_FRONTEND=noninteractive apt-get update -qq > /dev/null
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends -qq git-core build-essential fakeroot devscripts debhelper python-setuptools python-all python-support python-dateutil > /dev/null

mkdir -p ~/.ssh
echo '|1|sHRXzAmag5MqMsCeKD9BmOhagtY=|+G4gxq9iWiwvSDRrYIS+k/DJ7ko= ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==' >> ~/.ssh/known_hosts
echo '|1|pS1tYfKvNmzGxc1bhj2XEMOdEp4=|99GxsSrQQpuf4QiVKKy6cZ33DQ8= ssh-rsa AAAAB3NzaC1yc2EAAAABIwAAAQEAq2A7hRGmdnm9tUDbO9IDSwBK6TbQa+PXYPCPy6rbTrTtw7PHkccKrpp0yVhp5HdEIcKr6pLlVDBfOLX9QUsyCOV0wzfjIJNlGEYsdlLJizHhbn2mUjvSAHQqZETYP81eFzLQNnPHt4EVVUh7VfDESU84KezmD5QlWpXLmvU31/yMf+Se8xhHTvKSCZIFImWwoG6mbUoWf9nzpIoaSjB+weqqUUmpaaasXVal72J+UX2B+2RPW3RcT0eOzQgqlJL3RKrTJvdsjE3JEAvGq3lGHSZXy28G3skua2SmVi/w4yCE6gbODqnTWlg7+wC604ydGXA8VJiS5ap43JXiUFFAaQ==' >> ~/.ssh/known_hosts

rm -rf loghogd
git clone --quiet "$GIT_REPO" loghogd
cd loghogd

git submodule --quiet init
git submodule --quiet update


debuild -us -uc -I'.git'

dpkg -i ../loghog*_all.deb

cd

/etc/init.d/loghogd status
/etc/init.d/loghogd stop
/etc/init.d/loghogd start
/etc/init.d/loghogd restart
/etc/init.d/loghogd reload
/etc/init.d/loghogd status

exit 0
