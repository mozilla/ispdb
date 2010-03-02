import os
from settings import *

DEBUG = True
TEMPLATE_DEBUG = DEBUG

LOCAL_DEVELOPMENT = True

ISPDB_ROOT = os.path.dirname(__file__)

#set the database storage location to right inside the project root
DATABASE_NAME = os.path.join(ISPDB_ROOT, 'ispdb.sqlite')

# Absolute path to the directory that holds media.
MEDIA_ROOT = os.path.join(ISPDB_ROOT, 'media/')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a trailing slash.
ADMIN_MEDIA_PREFIX = '/admin_media/'
LOGIN_URL = '/openid/login'
LOGIN_REDIRECT_URL = '/'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(ISPDB_ROOT, "templates/"),
    os.path.join(ISPDB_ROOT, "templates/config/")
)

