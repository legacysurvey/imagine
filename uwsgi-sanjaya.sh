#! /bin/bash

BASE=/home/imagine
cd ${BASE}/decals-web

unset PYTHONPATH

export PYTHONPATH=${BASE}/astrometry:${BASE}/tractor:${BASE}/legacypipe/py:${BASE}/Django-2.2.5:.

uwsgi -s :3033 --plugin python36 --wsgi-file wsgi.py --touch-reload wsgi.py --processes 8 --reload-on-rss 768 -d /tmp/uwsgi.log


