"""
Django settings for Legacy Survey viewer project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

USER_QUERY_DIR = '/tmp/viewer-user'

REDIRECT_CUTOUTS_DECAPS = False

SDSS_PHOTOOBJS = None
SDSS_RESOLVE = None
SDSS_BASEDIR = '/global/cfs/cdirs/cosmo/data/sdss/dr14/'

CREATE_GALAXY_CATALOG = False

APPEND_SLASH = False

ENABLE_DEV = False

ENABLE_CUTOUTS = True

ENABLE_UNWISE = True

ENABLE_OLDER = True

# scientist view (vs public)
ENABLE_SCIENCE = True

# Collab-private data!
ENABLE_DESI_DATA = False

ENABLE_PANDAS = False

ENABLE_DESI_TARGETS = False
ENABLE_SPECTRA = False

ENABLE_DR5 = False
ENABLE_DR6 = True
ENABLE_DR7 = True
ENABLE_DR8 = True
ENABLE_DR8_MODELS = ENABLE_DR8
ENABLE_DR8_RESIDS = ENABLE_DR8
ENABLE_DR9SV = True

ENABLE_DR9 = False
ENABLE_DR9_MODELS = False
ENABLE_DR9_RESIDS = False
ENABLE_DR9_NORTH = False
ENABLE_DR9_NORTH_MODELS = False
ENABLE_DR9_NORTH_RESIDS = False
ENABLE_DR9_SOUTH = False
ENABLE_DR9_SOUTH_MODELS = False
ENABLE_DR9_SOUTH_RESIDS = False

ENABLE_DR10 = False
ENABLE_DR10_EARLY = False
ENABLE_DR10A = False

ENABLE_UNWISE_W3W4 = False

ENABLE_DR56 = False
ENABLE_DR67 = True

ENABLE_DECAPS = True
ENABLE_PS1 = False
ENABLE_DES_DR1 = True

ENABLE_ZTF = False
ENABLE_EBOSS = False

ENABLE_HSC_DR2 = True

ENABLE_VLASS = True

ENABLE_PHAT = False

# Can the web service not create files under BASE_DIR?
READ_ONLY_BASEDIR = False

DEBUG_LOGGING = True

MAX_NATIVE_ZOOM = 15


# Tile cache is writable?
SAVE_CACHE = False

ROOT_URL = '/viewer'

HOSTNAME = 'legacysurvey.org'
SUBDOMAINS = ['a','b','c','d']
DOMAIN = HOSTNAME

STATIC_URL_PATH = '/static/'
STATIC_URL = ROOT_URL + STATIC_URL_PATH

TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'http://{s}.%s%s%s/tiles/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL, STATIC_URL_PATH)

CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)

DISCUSS_CUTOUT_URL = 'https://www.legacysurvey.org/viewer/cutout.jpg'

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR   = os.path.dirname(__file__)
WEB_DIR    = os.path.dirname(BASE_DIR)
DATA_DIR   = os.path.join(WEB_DIR, 'data')
DUST_DIR   = os.path.join(DATA_DIR, 'dust')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
try:
    import secrets.django
    SECRET_KEY = secrets.django.SECRET_KEY
except:
    import random
    SECRET_KEY = ''.join([random.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)")
                          for i in range(50)])

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

TEMPLATE_DIRS = (os.path.join(WEB_DIR, 'templates'),)

TEMPLATE_CONTEXT_PROCESSORS = [
    #"django.contrib.auth.context_processors.auth",
    "django.template.context_processors.debug",
    #"django.template.context_processors.i18n",
    #"django.template.context_processors.media",
    "django.template.context_processors.static",
    #"django.template.context_processors.tz",
    #"django.contrib.messages.context_processors.messages",
    ]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': False,
        'DIRS': [os.path.join(WEB_DIR, 'templates')],
        'OPTIONS': {
            'context_processors': [
                "django.template.context_processors.debug",
                "django.template.context_processors.static",
                ],
            #'debug': True,
            },
    },
]

ALLOWED_HOSTS = [
    'legacysurvey.org', 'www.legacysurvey.org',
    'a.legacysurvey.org', 'b.legacysurvey.org', 'c.legacysurvey.org', 'd.legacysurvey.org',
    'imagine.legacysurvey.org',
    'decaps.legacysurvey.org',
    'm33.legacysurvey.org',
    'a.imagine.legacysurvey.org',
    'b.imagine.legacysurvey.org',
    'c.imagine.legacysurvey.org',
    'd.imagine.legacysurvey.org',
    'testserver',
    'localhost',
    # NERSC Spin Rancher2
    'spin.legacysurvey.org',
    'viewer.legacysurvey.org', 'a.viewer.legacysurvey.org', 'b.viewer.legacysurvey.org', 'c.viewer.legacysurvey.org', 'd.viewer.legacysurvey.org',
    'dev.viewer.legacysurvey.org', 'dev-a.viewer.legacysurvey.org', 'dev-b.viewer.legacysurvey.org', 'dev-c.viewer.legacysurvey.org', 'dev-d.viewer.legacysurvey.org',
    'lb.cosmo-viewer.production.svc.spin.nersc.org'
]

# Application definition

INSTALLED_APPS = (
    # 'django.contrib.admin',
    # 'django.contrib.auth',
    'django.contrib.contenttypes',
    # 'django.contrib.sessions',
    # 'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'cat',
)

MIDDLEWARE_CLASSES = (
#    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
#    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
#    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'viewer.urls'

WSGI_APPLICATION = 'wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
#     },
#     'cosmo': secrets.database.COSMO_DB,
#     'dr2': secrets.database.DR2_DB,
}
#DATABASE_ROUTERS = ['cat.models.Router']

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATICFILES_DIRS = (
    os.path.join(WEB_DIR, 'static'),
)

STATIC_ROOT = os.path.join(WEB_DIR, 'static')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'filters': None,
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

