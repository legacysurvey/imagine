#! /bin/bash

#cd /project/projectdirs/cosmo/webapp/viewer
#source ./venv/bin/activate
#export PYTHONPATH=${PYTHONPATH}:$(pwd)/venv

cd /project/projectdirs/cosmo/webapp/viewer
unset PYTHONPATH
export PATH=~/miniconda2/bin:${PATH}
source activate viewer-conda
export PYTHONPATH=${PYTHONPATH}:$(pwd)/viewer-conda

which uwsgi

uwsgi -s :3033 --wsgi-file wsgi.py --touch-reload wsgi.py --processes 8 --reload-on-rss 768 --logto /tmp/uwsgi.log -d /tmp/uwsgi2.log
#uwsgi -s :3331 --wsgi-file wsgi.py --touch-reload wsgi.py --processes 8 --reload-on-rss 768 --logto /tmp/uwsgi-3331.log -d /tmp/uwsgi2-3331.log


