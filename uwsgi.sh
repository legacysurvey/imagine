#! /bin/bash

cd /project/projectdirs/cosmo/webapp/viewer
export PYTHONPATH=${PYTHONPATH}:$(pwd)/venv/lib/python2.7:$(pwd)/venv
export PATH=$(pwd)/venv/bin:${PATH}

#uwsgi --plugin python -s :3031 --wsgi-file wsgi.py --processes 8 --logto /tmp/uwsgi.log --touch-reload wsgi.py
uwsgi -s :3031 --wsgi-file wsgi.py --processes 8 --reload-on-rss 768 --logto /tmp/uwsgi.log --touch-reload wsgi.py -d /tmp/uwsgi2.log



