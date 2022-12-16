from viewer.settings_common import *

DEBUG = True

DEBUG_LOGGING = True

READ_ONLY_BASEDIR = True

USER_QUERY_DIR = '/tmp/viewer-user'

FORCE_SCRIPT_NAME = ROOT_URL

STATIC_TILE_URL_B = 'https://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_DR5  = True

ENABLE_DR9 = True
ENABLE_DR9_MODELS = True
ENABLE_DR9_RESIDS = True

ENABLE_DR9_NORTH = True
ENABLE_DR9_NORTH_MODELS = True
ENABLE_DR9_NORTH_RESIDS = True

ENABLE_DR9_SOUTH = True
ENABLE_DR9_SOUTH_MODELS = True
ENABLE_DR9_SOUTH_RESIDS = True

ENABLE_DR9SV = False

ENABLE_DR10 = True

ENABLE_DESI_TARGETS = True
ENABLE_SPECTRA = True
