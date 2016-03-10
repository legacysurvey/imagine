import os
from settings_common import *

MAX_NATIVE_ZOOM = 15
SAVE_CACHE = True

ENABLE_WL = False
ENABLE_VCC = False

#HOSTNAME = 'test.legacysurvey.org'
HOSTNAME = 'localhost'

ROOT_URL = ''
#SUBDOMAINS = ['i']
SUBDOMAINS = ['a']


#STATIC_URL = 'http://%s%s/static/' % (HOSTNAME, ROOT_URL)
#STATIC_URL = 'http://legacysurvey.org/viewer-dev/static/'
STATIC_URL = '/static/'

#STATICFILES_DIRS = []
STATIC_ROOT = None

TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

#CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)
CAT_URL = '/{id}/{ver}/{z}/{x}/{y}.cat.json'

#STATIC_TILE_URL = 'http://{s}.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
STATIC_TILE_URL = 'http://{s}.legacysurvey.org/viewer-dev/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'

#os.environ['DECALS_DIR'] = os.path.join(DATA_DIR, 'decals-dr1')
#STATIC_URL = 'http://test.legacysurvey.org/static/'
#STATIC_TILE_URL = 'http://{s}.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
# DUST_DIR = '/project/projectdirs/cosmo/webapp/viewer/dust'
# UNWISE_DIR = '/project/projectdirs/cosmo/data/unwise/unwise-coadds'

