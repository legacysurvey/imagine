from viewer.settings_common import *

ALLOWED_HOSTS.extend(['cloud.legacysurvey.org',
                      'a.cloud.legacysurvey.org',
                      'b.cloud.legacysurvey.org',
                      'c.cloud.legacysurvey.org',
                      'd.cloud.legacysurvey.org',])

REDIRECT_CUTOUTS_DECAPS = True

MAX_NATIVE_ZOOM = 15
SAVE_CACHE = False

ENABLE_DEV = True
ENABLE_DR9SV = False
ENABLE_DR5 = False
ENABLE_DR6 = False
ENABLE_DR7 = False

ENABLE_DR67 = False
ENABLE_DR8_MODELS = False
ENABLE_DR8_RESIDS = False

ENABLE_DR8_NORTH = False
ENABLE_DR8_NORTH_MODELS = ENABLE_DR8_NORTH
ENABLE_DR8_NORTH_RESIDS = ENABLE_DR8_NORTH
ENABLE_DR8_SOUTH = False
ENABLE_DR8_SOUTH_MODELS = ENABLE_DR8_SOUTH
ENABLE_DR8_SOUTH_RESIDS = ENABLE_DR8_SOUTH

ENABLE_DECAPS = False

ENABLE_UNWISE = True
ENABLE_UNWISE_CATALOG = False

ENABLE_DES_DR1 = False
ENABLE_HSC_DR2 = True

ENABLE_VLASS = True

ENABLE_CUTOUTS = True

HOSTNAME = 'cloud.legacysurvey.org'
ROOT_URL = ''
SUBDOMAINS = [] #'a','b','c','d']

STATIC_URL = 'http://%s%s/static/' % (HOSTNAME, ROOT_URL)

# TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
# CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)
# STATIC_TILE_URL = 'http://{s}.cloud.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'

TILE_URL = 'http://%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

#CAT_URL = 'http://%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)
CAT_URL = 'http://www.legacysurvey.org/viewer-dev/{id}/{ver}/{z}/{x}/{y}.cat.json'
SMALL_CAT_URL = 'http://www.legacysurvey.org/viewer-dev/{id}/{ver}/cat.json?ralo=\{ralo\}&rahi=\{rahi\}&declo=\{declo\}&dechi=\{dechi\}'

STATIC_TILE_URL = 'http://cloud.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'

NERSC_TILE_URL = 'http://www.legacysurvey.org/viewer/{id}/{ver}/{z}/{x}/{y}.jpg'

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = ['a','b','c','d']
