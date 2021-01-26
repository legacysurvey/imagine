from viewer.settings_common import *

ROOT_URL = '/'
STATIC_URL_PATH = 'static/'
STATIC_URL = ROOT_URL + STATIC_URL_PATH

HOSTNAME = 'dev.viewer.legacysurvey.org'
TILE_URL = 'https://dev-{s}.%s%s{id}/{ver}/{z}/{x}/{y}.jpg' % ('viewer.legacysurvey.org', ROOT_URL)

DEBUG = True

DEBUG_LOGGING = True

READ_ONLY_BASEDIR = True

USER_QUERY_DIR = '/tmp/viewer-user'

FORCE_SCRIPT_NAME = ROOT_URL

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_DR5  = False
ENABLE_DR9 = True
ENABLE_DR9SV = False
ENABLE_OLDER = False
# public version
ENABLE_SCIENCE = False
ENABLE_DESI_TARGETS = False
ENABLE_SPECTRA = False
ENABLE_DR9_MODELS = False
ENABLE_DR9_RESIDS = False
ENABLE_DR9_SOUTH = False
ENABLE_DR9_SOUTH_MODELS = False
ENABLE_DR9_SOUTH_RESIDS = False
ENABLE_CUTOUTS = False
