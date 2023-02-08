#!/bin/bash
# Working dir: /app
# We expect the "viewer" volume mount to include a legacypipe checkout!
#export PYTHONPATH=$(pwd)/legacypipe/py:$PYTHONPATH
export PYTHONPATH=$(pwd)/tractor:$PYTHONPATH
export PYTHONPATH=$(pwd)/viewer:$PYTHONPATH
cd viewer
uwsgi --touch-reload wsgi.py --ini uwsgi-rancher2.ini
#--stats 127.0.0.1:1717
