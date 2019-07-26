from viewer.settings_common import *

ENABLE_DR2 = False
ENABLE_DR3 = False
ENABLE_DR5 = False
ENABLE_DR6 = False
ENABLE_DR7 = False
ENABLE_DR8 = True

# ALLOWED_HOSTS.append('127.0.0.1')
# ALLOWED_HOSTS.append('localhost')
ALLOWED_HOSTS.append('45.77.1.19')
ALLOWED_HOSTS.append('viewer.legacysurvey.org')

CREATE_GALAXY_CATALOG = False

#STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
#SUBDOMAINS_B = ['a','b','c','d']
SUBDOMAINS_B = []
# > ssh cori -L 5432:scidb2.nersc.gov:5432

DATABASE_ROUTERS = ['cat.models.Router']

ENABLE_WL = False
ENABLE_VCC = False

#HOSTNAME = 'test.legacysurvey.org'
HOSTNAME = 'localhost'

ROOT_URL = ''
#SUBDOMAINS = ['i']
#SUBDOMAINS = ['a']
SUBDOMAINS = []

#STATIC_URL = 'http://%s%s/static/' % (HOSTNAME, ROOT_URL)
#STATIC_URL = 'http://legacysurvey.org/viewer-dev/static/'
STATIC_URL = '/static/'

#STATICFILES_DIRS = []
STATIC_ROOT = None

#TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
#TILE_URL = 'http://%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
# TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % ('legacysurvey.org', '/viewer-dev')
TILE_URL = 'http://{id}.legacysurvey.org/{z}/{x}/{y}.jpg'

#CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)

CAT_URL = '/{id}/{ver}/{z}/{x}/{y}.cat.json'

# No CORS
#CAT_URL = 'http://legacysurvey.org/viewer-dev/{id}/{ver}/{z}/{x}/{y}.cat.json'

#STATIC_TILE_URL = 'http://{s}.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
#STATIC_TILE_URL = 'http://{s}.legacysurvey.org/viewer-dev/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
STATIC_TILE_URL = TILE_URL
STATIC_TILE_URL_B = TILE_URL
#os.environ['DECALS_DIR'] = os.path.join(DATA_DIR, 'decals-dr1')
#STATIC_URL = 'http://test.legacysurvey.org/static/'
#STATIC_TILE_URL = 'http://{s}.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
# DUST_DIR = '/project/projectdirs/cosmo/webapp/viewer/dust'
# UNWISE_DIR = '/project/projectdirs/cosmo/data/unwise/unwise-coadds'

