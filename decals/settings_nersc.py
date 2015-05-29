from settings_common import *

# no CORS -- so don't use subdomains
CAT_URL = 'http://%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)

ENABLE_NEXP = False
