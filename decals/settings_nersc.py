from settings_common import *

DEBUG_LOGGING = True

READ_ONLY_BASEDIR = True

USER_QUERY_DIR = '/tmp/viewer-user'

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_CUTOUTS = False

ENABLE_VCC  = False
ENABLE_WL   = False
ENABLE_DR2  = True

SDSS_PHOTOOBJS = '/project/projectdirs/cosmo/data/sdss/dr10/boss/photoObj'
SDSS_RESOLVE = '/project/projectdirs/cosmo/data/sdss/pre13/eboss/resolve/2013-07-29'

