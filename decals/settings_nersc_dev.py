from settings_common import *

READ_ONLY_BASEDIR = True

ROOT_URL = '/viewer-dev'
STATIC_URL_PATH = '/viewer-dev/static'

STATIC_URL = 'http://%s%s/' % (HOSTNAME, STATIC_URL_PATH)
TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
STATIC_TILE_URL = 'http://{s}.%s%s/tiles/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, STATIC_URL_PATH)

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_NEXP = False
ENABLE_VCC  = False
ENABLE_WL   = False
ENABLE_DR2  = True
ENABLE_DEPTH = False

#SDSS_PHOTOOBJS = '/project/projectdirs/cosmo/data/sdss/pre13/eboss/photoObj.v5b'

SDSS_PHOTOOBJS = '/project/projectdirs/cosmo/data/sdss/dr10/boss/photoObj'
SDSS_RESOLVE = '/project/projectdirs/cosmo/data/sdss/pre13/eboss/resolve/2013-07-29'

