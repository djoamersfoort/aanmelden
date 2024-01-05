"""
Django settings for aanmelden project.
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'jkweifgjewifjwiojfweiojfweiojfweiojfweiojfweijfweijfi'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',
    'mathfilters',
    'aanmelden.src'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'aanmelden.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'aanmelden', 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'aanmelden.wsgi.application'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/
LANGUAGE_CODE = 'nl-nl'
TIME_ZONE = 'Europe/Amsterdam'
USE_I18N = True
USE_L10N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = '/srv/static'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "aanmelden", "static"),
)

# IDP Settings
LOGIN_REDIRECT_URL = '/main/'
LOGIN_URL = '/'
IDP_CLIENT_ID = '<idp client id>'
IDP_CLIENT_SECRET = '<idp client secret>'
IDP_REDIRECT_URL = 'http://localhost:8000/oauth/'
IDP_AUTHORIZE_URL = 'https://leden.djoamersfoort.nl/o/authorize/'
IDP_TOKEN_URL = 'https://leden.djoamersfoort.nl/o/token/'
IDP_API_URL = 'https://leden.djoamersfoort.nl/api/v1/member/details'
IDP_LOGOUT_URL = 'https://leden.djoamersfoort.nl/accounts/logout/'
IDP_API_SCOPES = ['user/basic', 'user/names', 'user/email']
INTROSPECTION_CLIENT_ID = '<client id>'
INTROSPECTION_CLIENT_SECRET = '<client secret>'
IDP_INTROSPECTION_URL = 'https://leden.djoamersfoort.nl/o/introspect/'
OPENID_CONFIGURATION = 'https://leden.djoamersfoort.nl/o/.well-known/openid-configuration/'
# Corvee is allowed to call the 'presence' API
API_CLIENT_WHITELIST = ['xxxxxxx']

SESSION_COOKIE_SECURE = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True

# Map of #tutors -> additional slots
SLOT_LEVELS = {
    0: 16,
    1: 4,
    5: 4,
    6: 2,
    7: 2,
}
