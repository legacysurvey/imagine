"""
Django settings for decals project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

import secrets.django
import secrets.database

GAIA_CAT_DIR = '/project/projectdirs/cosmo/work/gaia/chunks-gaia_rel1'

APPEND_SLASH = False

# Enable Virgo Cluster Catalog layer?
ENABLE_VCC = False
# Enable DECaLS Weak Lensing map?
ENABLE_WL = False
ENABLE_CUTOUTS = True
ENABLE_SQL = False

ENABLE_DR2 = True
ENABLE_DR3 = True
ENABLE_DR4 = True
ENABLE_DR5 = False

ENABLE_DECAPS = False
ENABLE_PS1 = False

# Can the web service not create files under BASE_DIR?
READ_ONLY_BASEDIR = False

DEBUG_LOGGING = False

SDSS_PHOTOOBJS = None
SDSS_RESOLVE = None

MAX_NATIVE_ZOOM = 15


# Tile cache is writable?
SAVE_CACHE = False

ROOT_URL = '/viewer'
HOSTNAME = 'legacysurvey.org'
SUBDOMAINS = ['a','b','c','d']

STATIC_URL_PATH = '/static/'
STATIC_URL = 'http://%s%s%s' % (HOSTNAME, ROOT_URL, STATIC_URL_PATH)

TILE_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL)

STATIC_TILE_URL = 'http://{s}.%s%s%s/tiles/{id}/{ver}/{z}/{x}/{y}.jpg' % (HOSTNAME, ROOT_URL, STATIC_URL_PATH)

CAT_URL = 'http://{s}.%s%s/{id}/{ver}/{z}/{x}/{y}.cat.json' % (HOSTNAME, ROOT_URL)

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR   = os.path.dirname(__file__)
WEB_DIR    = os.path.dirname(BASE_DIR)
DATA_DIR   = os.path.join(WEB_DIR, 'data')
DUST_DIR   = os.path.join(DATA_DIR, 'dust')
HALPHA_DIR = os.path.join(DATA_DIR, 'halpha')
UNWISE_DIR = os.path.join(DATA_DIR, 'unwise-coadds')
UNWISE_NEO1_DIR = os.path.join(DATA_DIR, 'unwise-coadds-neo1')
UNWISE_NEO2_DIR = os.path.join(DATA_DIR, 'unwise-coadds-neo2')
SDSS_DIR   = os.path.join(DATA_DIR, 'sdss')

#DUST_DIR = '/project/projectdirs/cosmo/webapp/viewer/dust'
#UNWISE_DIR = '/project/projectdirs/cosmo/data/unwise/unwise-coadds'

#os.environ['DECALS_DIR'] = '/project/projectdirs/cosmo/webapp/viewer/decals-dr1/'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = secrets.django.SECRET_KEY

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
        #'APP_DIRS': True,
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
    'a.imagine.legacysurvey.org',
    'b.imagine.legacysurvey.org',
    'c.imagine.legacysurvey.org',
    'd.imagine.legacysurvey.org',
]

# Application definition

INSTALLED_APPS = (
    # 'django.contrib.admin',
    # 'django.contrib.auth',
    'django.contrib.contenttypes',
    #'django.contrib.sessions',
    #    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cat',
)

MIDDLEWARE_CLASSES = (
#    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
#    'django.middleware.csrf.CsrfViewMiddleware',
#    'django.contrib.auth.middleware.AuthenticationMiddleware',
#    'django.contrib.messages.middleware.MessageMiddleware',
#    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'decals.urls'

WSGI_APPLICATION = 'wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    },
    'cosmo': secrets.database.COSMO_DB,
    'dr2': secrets.database.DR2_DB,
}

DATABASE_ROUTERS = ['cat.models.Router']

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

