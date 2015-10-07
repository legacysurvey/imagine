from settings_common import *

# no CORS -- so don't use subdomains, or specify hostname (www.legacysurvey.org vs legacysurvey.org)
CAT_URL = '%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (ROOT_URL)

ENABLE_NEXP = False
ENABLE_VCC  = False
ENABLE_WL   = False
ENABLE_DR2  = False
ENABLE_DEPTH = False
