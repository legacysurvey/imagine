from viewer.settings_common import *

INDEX_KWARGS = dict(merian_first=True)

FLAVOUR = 'viewer-merian'
ROOT_URL = '/viewer-merian'
STATIC_URL_PATH = '/viewer-merian/static/'
FORCE_SCRIPT_NAME = ROOT_URL

print('Merian: original TILE URL', TILE_URL)

# Nope can't do subdomains because of password!
#MY_TILE_URL = 'https://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
MY_TILE_URL = 'https://%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)
print('My tile URL:', MY_TILE_URL)
MY_SUBDOMAINS = SUBDOMAINS

maxZoom = 16
maxnative = 14
my_url = [0, maxZoom, MY_TILE_URL, MY_SUBDOMAINS]
LAYER_OVERRIDES = {
    #'merian-n540': ['Merian N540', [my_url], maxnative, 'MERIAN collaboration'],
    #'merian-n708': ['Merian N708', [my_url], maxnative, 'MERIAN collaboration'],
    'merian-n540': [my_url],
    'merian-n708': [my_url],
    'merian-n540-bw': [my_url],
    'merian-n708-bw': [my_url],
}

DEBUG = True

DEBUG_LOGGING = True

READ_ONLY_BASEDIR = True

USER_QUERY_DIR = '/tmp/viewer-user'

FORCE_SCRIPT_NAME = ROOT_URL

STATIC_TILE_URL_B = 'https://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_MERIAN = True

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

ENABLE_DESI_TARGETS = False
ENABLE_SPECTRA = True
