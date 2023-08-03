from viewer.settings_common import *

HOSTNAME = 'www.legacysurvey.org'

DEBUG = True
DEBUG_LOGGING = False

USER_QUERY_DIR = '/tmp/viewer-erosita-user'

READ_ONLY_BASEDIR = True

ROOT_URL = '/viewer-erosita'
STATIC_URL_PATH = '/viewer-erosita/static/'
FORCE_SCRIPT_NAME = ROOT_URL

MY_TILE_URL = 'https://%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
MY_SUBDOMAINS = []


STATIC_URL = STATIC_URL_PATH
#TILE_URL = 'https://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
STATIC_TILE_URL = 'https://{s}.%s%s/tiles/{id}/{ver}/{z}/{x}/{y}.jpg' % (DOMAIN, STATIC_URL_PATH)
STATIC_TILE_URL_B = 'https://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

my_url = [0, maxZoom, MY_TILE_URL, MY_SUBDOMAINS]
LAYER_OVERRIDES = {
    'erosita-efeds': [my_url],
}

ENABLE_DEV = True

ENABLE_EROSITA = True

ENABLE_DECAPS = True
ENABLE_EBOSS = True
ENABLE_DR5 = True
ENABLE_PS1 = False
ENABLE_DR8 = True
ENABLE_DR9SV = False
ENABLE_DES_DR1 = True

ENABLE_SPECTRA = True

ENABLE_DR9 = True
ENABLE_DR9_MODELS = True
ENABLE_DR9_RESIDS = True

ENABLE_DR9_NORTH = False
ENABLE_DR9_NORTH_MODELS = True
ENABLE_DR9_NORTH_RESIDS = True

ENABLE_DR9_SOUTH = False
ENABLE_DR9_SOUTH_MODELS = True
ENABLE_DR9_SOUTH_RESIDS = True
