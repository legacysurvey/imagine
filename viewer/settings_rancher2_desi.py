from viewer.settings_common import *

HOSTNAME = 'www.legacysurvey.org'

DEBUG = True
DEBUG_LOGGING = False

USER_QUERY_DIR = '/tmp/viewer-desi-user'

READ_ONLY_BASEDIR = True

ROOT_URL = '/viewer-desi'
STATIC_URL_PATH = '/viewer-desi/static/'

FORCE_SCRIPT_NAME = ROOT_URL

STATIC_URL = STATIC_URL_PATH
#TILE_URL = 'https://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
TILE_URL = 'https://%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'https://{s}.%s%s/tiles/{id}/{ver}/{z}/{x}/{y}.jpg' % (DOMAIN, STATIC_URL_PATH)

# save the "production" subdomains in settings_common
SUBDOMAINS_PROD = SUBDOMAINS

# each sub-domain would want to ask for the desi password.
SUBDOMAINS = []

STATIC_TILE_URL_B = 'https://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS_PROD

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_DEV = True

ENABLE_DECAPS = True
ENABLE_EBOSS = True
ENABLE_DR5 = True
ENABLE_PS1 = True
ENABLE_DR8 = True
ENABLE_DES_DR1 = True
ENABLE_PHAT = True

# Collab-private data!
ENABLE_DESI_DATA = True

ENABLE_DESI_TARGETS = True
ENABLE_SPECTRA = True

ENABLE_DR10 = True
ENABLE_DR11 = True

ENABLE_DR9 = True
ENABLE_DR9_MODELS = True
ENABLE_DR9_RESIDS = True

ENABLE_DR9_NORTH = True
ENABLE_DR9_NORTH_MODELS = True
ENABLE_DR9_NORTH_RESIDS = True

ENABLE_DR9_SOUTH = True
ENABLE_DR9_SOUTH_MODELS = True
ENABLE_DR9_SOUTH_RESIDS = True
