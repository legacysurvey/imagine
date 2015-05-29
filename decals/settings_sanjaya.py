import os
from settings_common import *

MAX_NATIVE_ZOOM = 13
SAVE_CACHE = True

HOSTNAME = 'imagine.legacysurvey.org'
ROOT_URL = ''
SUBDOMAINS = ['a','b','c','d']

STATIC_URL = 'http://%s%s/static/' % (HOSTNAME, ROOT_URL)

TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'

os.environ['DECALS_DIR'] = os.path.join(DATA_DIR, 'decals-dr1')

