#~ Copyright (C) 2010 Nokia Corporation and/or its subsidiary(-ies).
#~ Contact: Ramez Hanna <ramez.hanna@nokia.com>
#~ This program is free software: you can redistribute it and/or modify
#~ it under the terms of the GNU General Public License as published by
#~ the Free Software Foundation, either version 3 of the License, or
#~ (at your option) any later version.

#~ This program is distributed in the hope that it will be useful,
#~ but WITHOUT ANY WARRANTY; without even the implied warranty of
#~ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#~ GNU General Public License for more details.

#~ You should have received a copy of the GNU General Public License
#~ along with this program.  If not, see <http://www.gnu.org/licenses/>

# Django settings for img project.
from os.path import abspath, dirname, join
PROJECT_DIR = dirname(__file__)

IMGCONF="/etc/imager/img.conf"

import configparser
config = configparser.ConfigParser()
try:
    with open(IMGCONF) as c:
        config.read_file(c)
except Exception:
    try:
        # during docs build
        with open("src/img_web/img.conf") as c:
            config.read_file(c)
    except IOError:
        # when developing it is in cwd
        with open("img.conf") as c:
            config.read_file(c)

url_prefix = config.get('web', 'url_prefix')
static_media_collect = config.get('web', 'static_media_collect')
TEMPLATESDIR = config.get('web', 'templates_dir')
FEATURESDIR = config.get('web', 'features_dir')
USE_REMOTE_AUTH = config.getboolean('web', 'use_http_remote_user')
ALLOWED_HOSTS = config.get('web', 'allowed_hosts').split(",")

boss_host = config.get('boss', 'boss_host')
boss_user = config.get('boss', 'boss_user')
boss_pass = config.get('boss', 'boss_pass')
boss_vhost = config.get('boss', 'boss_vhost')

db_engine = config.get('db', 'db_engine')
db_name = config.get('db', 'db_name')
db_user = config.get('db', 'db_user')
db_pass = config.get('db', 'db_pass')
db_host = config.get('db', 'db_host')

create_image_process = config.get('processes', 'create_image_process')

DEVICEGROUP = config.get('test', 'devicegroup')


USE_LDAP = config.getboolean('ldap', 'use_ldap')
USE_SEARCH = config.getboolean('ldap', 'use_search')
if USE_LDAP:

  import ldap
  from django_auth_ldap.config import LDAPSearch
  import logging
  
  LDAP_SERVER = config.get('ldap', 'ldap_server')
  ldap_verify_cert = config.getboolean('ldap', 'verify_certificate')

  if USE_SEARCH:
    AUTH_LDAP_USER_SEARCH = LDAPSearch( config.get('ldap', 'ldap_base_dn', raw=True),
                                        ldap.SCOPE_SUBTREE,
                                        config.get('ldap', 'ldap_filter', raw=True))
  else:
    AUTH_LDAP_USER_DN_TEMPLATE = config.get('ldap', 'ldap_dn_template', raw=True)
  
  mail_attr = config.get('ldap', 'ldap_mail_attr', raw=True)
  fname_attr = config.get('ldap', 'ldap_fname_attr', raw=True)
  lname_attr = config.get('ldap', 'ldap_lname_attr', raw=True)
  AUTH_LDAP_USER_ATTR_MAP = {"first_name" : fname_attr, "last_name" : lname_attr, "email":mail_attr}
elif USE_REMOTE_AUTH:
    AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.RemoteUserBackend',
    )

SECRET_KEY = config.get('web', 'secret_key')

DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS
DATABASES = {
            'default': {
                'ENGINE' : 'django.db.backends.' + db_engine,
                'NAME' : db_name,
                'USER' : db_user,
                'PASSWORD' : db_pass,
                'HOST' : db_host,
                'PORT' : '',
                }
            }

DATABASE_OPTIONS = {
            "autocommit": True,
            }

# Django 3.2 needs the auto primary key to be defined
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = None

# Timezone support is disabled as this is the default pre-5.0 and is
# how the code is written
# Setting explicitly as it changes to True in Django 5.0
# This may need to be reviewed.
USE_TZ = False

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = static_media_collect

STATIC_URL = '/' + url_prefix + '/site_media/'

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'img_web.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [join(PROJECT_DIR,'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.request",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'taggit',
    'img_web.app',
)

FORCE_SCRIPT_NAME = ''

LOGIN_URL='/' + url_prefix + "/login/"
LOGIN_REDIRECT_URL='/' + url_prefix + "/"

if USE_LDAP:

  logger = logging.getLogger('django_auth_ldap')
  logger.addHandler(logging.StreamHandler())
  logger.setLevel(logging.DEBUG)

  AUTH_LDAP_SERVER_URI = LDAP_SERVER
  if not ldap_verify_cert :
      AUTH_LDAP_GLOBAL_OPTIONS = {
      ldap.OPT_X_TLS_REQUIRE_CERT : ldap.OPT_X_TLS_NEVER
      }

  AUTHENTICATION_BACKENDS = (
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
  )
elif USE_REMOTE_AUTH:
  MIDDLEWARE_CLASSES += ( 'django.contrib.auth.middleware.RemoteUserMiddleware',)

