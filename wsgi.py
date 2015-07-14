"""
WSGI config for decals project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/howto/deployment/wsgi/
"""

import os
os.environ.setdefault('DECALS_DIR', '/project/projectdirs/cosmo/work/decam/versions/work')
os.environ.setdefault('BOSS_PHOTOOBJ', '/project/projectdirs/cosmo/data/sdss/pre13/eboss/photoObj.v5b')
os.environ.setdefault('PHOTO_RESOLVE', '/project/projectdirs/cosmo/data/sdss/pre13/eboss/resolve/2013-07-29')
os.environ.setdefault('PHOTO_REDUX', '')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "decals.settings")

import django
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

