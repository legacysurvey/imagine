from viewer.settings_common import *

# Quieter, for cutouts.py
DEBUG_LOGGING = False
INFO_LOGGING = False

ENABLE_DR5 = True
ENABLE_DR6 = True
ENABLE_DR7 = True

ALLOWED_HOSTS.append('127.0.0.1')
ALLOWED_HOSTS.append('localhost')

CREATE_GALAXY_CATALOG = True

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = ['a','b','c','d']

# > ssh cori -L 5432:scidb2.nersc.gov:5432

DATABASE_ROUTERS = ['cat.models.Router']

MAX_NATIVE_ZOOM = 15
SAVE_CACHE = True

#HOSTNAME = 'test.legacysurvey.org'
HOSTNAME = 'localhost'

ROOT_URL = ''
SUBDOMAINS = []

STATIC_URL = '/static/'

STATIC_ROOT = None

TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % ('legacysurvey.org', '/viewer-dev')

CAT_URL = '/{id}/{ver}/{z}/{x}/{y}.cat.json'

# No CORS
STATIC_TILE_URL = 'http://{s}.legacysurvey.org/viewer-dev/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
