import os
from settings_common import *

HOSTNAME = 'test.legacysurvey.org'
ROOT_URL = ''
SUBDOMAINS = ['i']

STATIC_URL = 'http://%s%s/static/' % (HOSTNAME, ROOT_URL)

TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'http://{s}.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'

os.environ['DECALS_DIR'] = os.path.join(DATA_DIR, 'decals-dr1')

#STATIC_URL = 'http://test.legacysurvey.org/static/'

#STATIC_TILE_URL = 'http://{s}.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'

# DUST_DIR = '/project/projectdirs/cosmo/webapp/viewer/dust'
# UNWISE_DIR = '/project/projectdirs/cosmo/data/unwise/unwise-coadds'

