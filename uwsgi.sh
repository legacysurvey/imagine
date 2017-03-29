#! /bin/bash

cd /project/projectdirs/cosmo/webapp/viewer
source ./venv/bin/activate

#export PYTHONPATH=${PYTHONPATH}:$(pwd)/venv/lib/python2.7:$(pwd)/venv
#export PATH=$(pwd)/venv/bin:${PATH}

export PYTHONPATH=${PYTHONPATH}:$(pwd)/venv
#export PYTHONPATH=${PYTHONPATH}:.

echo "PYTHONPATH:"
echo $PYTHONPATH | tr : '\n'
echo

# /home/dstn/.local/lib/python2.7
# /usr/local/lib/python2.7
# .
# /home/dstn/cosmo/webapp/viewer-dev/venv
# /project/projectdirs/cosmo/webapp/viewer/venv
#

# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/site-packages/

# sgn04, viewer venv$ python -c "import sys; print '\n'.join(sys.path)"
# 
# /home/dstn/.local/lib/python2.7/site-packages/virtualenv-14.0.5-py2.7.egg
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/site-packages/pip-1.2.1-py2.7.egg
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/site-packages/setuptools-19.2-py2.7.egg
# /home/dstn/.local/lib/python2.7
# /usr/local/lib/python2.7
# /global/project/projectdirs/cosmo/webapp/viewer
# /home/dstn/cosmo/webapp/viewer-dev/venv
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python27.zip
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/plat-linux2
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/lib-tk
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/lib-old
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/lib-dynload
# /home/dstn/.local/lib/python2.7/site-packages
# /project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/site-packages



# '.',
#  '',
#  '/home/dstn/.local/lib/python2.7/site-packages/virtualenv-14.0.5-py2.7.egg',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/site-packages/pip-1.2.1-py2.7.egg',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/site-packages/setuptools-19.2-py2.7.egg',
#  '/home/dstn/.local/lib/python2.7',
#  '/usr/local/lib/python2.7',
#  '/project/projectdirs/cosmo/webapp/viewer/venv',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python27.zip',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/plat-linux2',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/lib-tk',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/lib-old',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/lib-dynload',
#  '/home/dstn/.local/lib/python2.7/site-packages',
#  '/global/project/projectdirs/cosmo/webapp/viewer/venv/lib/python2.7/site-packages']

uwsgi -s :3031 --wsgi-file wsgi.py --touch-reload wsgi.py --processes 8 --reload-on-rss 768 --logto /tmp/uwsgi.log -d /tmp/uwsgi2.log


