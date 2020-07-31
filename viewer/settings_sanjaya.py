from viewer.settings_common import *

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
ENABLE_DECAPS = False

ENABLE_UNWISE = False

ENABLE_DES_DR1 = False
ENABLE_HSC_DR2 = False

ENABLE_VLASS = False

ENABLE_CUTOUTS = False

HOSTNAME = 'imagine.legacysurvey.org'
ROOT_URL = ''
SUBDOMAINS = ['a','b','c','d']

STATIC_URL = 'http://%s%s/static/' % (HOSTNAME, ROOT_URL)

TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS
