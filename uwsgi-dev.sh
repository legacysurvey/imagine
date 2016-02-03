#! /bin/bash

cd /project/projectdirs/cosmo/webapp/viewer-dev
source ./venv2/bin/activate
export PYTHONPATH=${PYTHONPATH}:$(pwd)/venv2
#export PYTHONPATH=${PYTHONPATH}:$(pwd)/venv/lib/python2.7:$(pwd)/venv
#export PATH=$(pwd)/venv/bin:${PATH}

uwsgi -s :3032 --wsgi-file wsgi.py --touch-reload wsgi.py --processes 4 --reload-on-rss 320 --logto /tmp/uwsgi-dev.log -d /tmp/uwsgi2-dev.log



