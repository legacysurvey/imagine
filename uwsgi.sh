#! /bin/bash

cd /project/projectdirs/cosmo/webapp/viewer

#source ./venv/bin/activate
#export PYTHONPATH=${PYTHONPATH}:$(pwd)/venv
#export PYTHONPATH=${PYTHONPATH}:$(pwd)/venv/lib/python2.7:$(pwd)/venv
#export PATH=$(pwd)/venv/bin:${PATH}

unset PYTHONPATH
export PATH=~/miniconda3b/bin:${PATH}
#source activate viewer-conda-2
source activate viewer-conda-3
which uwsgi
uwsgi --version
echo $PATH
export PYTHONPATH=${PYTHONPATH}:${CONDA_PREFIX}
export LD_LIBRARY_PATH=${CONDA_PREFIX}/lib

uwsgi -s :3033 --wsgi-file wsgi.py --touch-reload wsgi.py --processes 8 --reload-on-rss 768 -d /tmp/uwsgi2.log --limit-post 50000000


