#! /bin/bash

cd /project/projectdirs/cosmo/webapp/viewer-dev

unset PYTHONPATH

export PATH=~/miniconda2/bin:${PATH}
source activate viewer-dev-conda

export PYTHONPATH=${PYTHONPATH}:$(pwd)/viewer-dev-conda

# echo "PYTHONPATH:"
# echo $PYTHONPATH | tr : '\n'
# echo "python sys.path:"
# python -c "import sys; print '\n'.join(sys.path)"
# echo
# which uwsgi

uwsgi -s :3032 --wsgi-file wsgi.py --touch-reload wsgi.py --processes 4 --reload-on-rss 320 --logto /tmp/uwsgi-dev.log -d /tmp/uwsgi2-dev.log



