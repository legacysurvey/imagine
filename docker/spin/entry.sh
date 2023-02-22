#!/bin/bash
# Working dir: /app
# We expect the "viewer" volume mount to include a legacypipe checkout!
#export PYTHONPATH=$(pwd)/legacypipe/py:$PYTHONPATH
# Installed versions in /usr/local/lib/python
#export PYTHONPATH=/app/astrometry:$PYTHONPATH
#export PYTHONPATH=/app/tractor:$PYTHONPATH
export PYTHONPATH=/app/viewer:$PYTHONPATH

mkdir /tmp/matplotlib
export MPLCONFIGDIR=/tmp/matplotlib

cd /app/viewer
uwsgi --touch-reload wsgi.py --ini uwsgi-rancher2.ini
#--stats 127.0.0.1:1717
