from viewer.settings_common import *

REDIRECT_CUTOUTS_DECAPS = True

MAX_NATIVE_ZOOM = 15
SAVE_CACHE = False

ENABLE_NEXP = False
ENABLE_VCC  = False
ENABLE_WL   = False
#ENABLE_DR2  = True

HOSTNAME = 'imagine.legacysurvey.org'
ROOT_URL = ''
SUBDOMAINS = ['a','b','c','d']

STATIC_URL = 'http://%s%s/static/' % (HOSTNAME, ROOT_URL)

TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

#os.environ['DECALS_DIR'] = os.path.join(DATA_DIR, 'decals-dr1')

