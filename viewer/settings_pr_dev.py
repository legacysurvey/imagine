from viewer.settings_common import *

# Allow direct access via the Elastic Beanstalk environment URL (test env, EB
# health checks). Production is reached via viewer.legacysurvey.org (already in
# ALLOWED_HOSTS); this just permits the *.elasticbeanstalk.com CNAMEs too.
ALLOWED_HOSTS = ALLOWED_HOSTS + ['.elasticbeanstalk.com']

ROOT_URL = '/'
STATIC_URL_PATH = 'static/'
STATIC_URL = ROOT_URL + STATIC_URL_PATH

HOSTNAME = 'dev.viewer.legacysurvey.org'
TILE_URL = 'https://dev-{s}.%s%s{id}/{ver}/{z}/{x}/{y}.jpg' % ('viewer.legacysurvey.org', ROOT_URL)

DEBUG = False
DEBUG_LOGGING = False

READ_ONLY_BASEDIR = True

USER_QUERY_DIR = '/tmp/viewer-user'

FORCE_SCRIPT_NAME = ROOT_URL

STATIC_TILE_URL_B = 'http://{s}.imagine.legacysurvey.org/static/tiles/{id}/{ver}/{z}/{x}/{y}.jpg'
SUBDOMAINS_B = SUBDOMAINS

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_DR5  = False
ENABLE_DR9 = True
# DR11: image layers served from S3 (dr11-{south,north}.legacysurvey.org, us-west-2),
# with dynamic-server fallback. Models/residuals remain dynamic (def_url).
ENABLE_DR11 = True
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

# DESI tile/spectra/daily overlays query per-release data on the dynamic server;
# that data is not on S3/in this container, so hide them from the overlay menu.
ENABLE_DESI_EDR = False
ENABLE_DESI_DR1 = False
ENABLE_DESI_DAILY_OBS = False
