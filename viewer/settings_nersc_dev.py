from viewer.settings_common import *

DEBUG_LOGGING = True

USER_QUERY_DIR = '/tmp/viewer-dev-user'

READ_ONLY_BASEDIR = True

ROOT_URL = '/viewer-dev'
STATIC_URL_PATH = '/viewer-dev/static'

FORCE_SCRIPT_NAME = ROOT_URL

STATIC_URL = STATIC_URL_PATH
TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'http://{s}.%s%s/tiles/{id}/{ver}/{z}/{x}/{y}.jpg' % (DOMAIN, STATIC_URL_PATH)

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_DEV = True

ENABLE_DR2  = False
ENABLE_DECAPS = True
ENABLE_EBOSS = True
ENABLE_DR3 = False
ENABLE_DR4 = False
ENABLE_DR5 = True
ENABLE_PS1 = True
ENABLE_DR8 = True
ENABLE_DR9SV = True
ENABLE_DES_DR1 = True

