from viewer.settings_common import *

#ENABLE_SQL = True

DEBUG_LOGGING = True
#DEBUG_LOGGING = False

USER_QUERY_DIR = '/tmp/viewer-dev-user'
#USER_CATALOG_DIR = USER_QUERY_DIR

READ_ONLY_BASEDIR = True

ROOT_URL = '/viewer-dev'
STATIC_URL_PATH = '/viewer-dev/static'

STATIC_URL = 'http://%s%s/' % (HOSTNAME, STATIC_URL_PATH)
TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'http://{s}.%s%s/tiles/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, STATIC_URL_PATH)

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

#ENABLE_SQL = True
#ENABLE_MZLS = True

ENABLE_DR2  = False
ENABLE_DECAPS = True
ENABLE_EBOSS = True
ENABLE_PS1 = True
#ENABLE_DR5 = True
#ENABLE_DR6 = True
#ENABLE_DR7 = True
ENABLE_DES_DR1 = True

