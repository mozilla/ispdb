import os, sys

#Calculate the path based on the location of the WSGI script.
apache_configuration= os.path.dirname(__file__)
project = os.path.dirname(apache_configuration)
workspace = os.path.dirname(project)
sys.path.append(workspace) 

print >> sys.stderr, "Path is %s" % sys.path

#Add the path to 3rd party django application and to django itself.
#sys.path.append('C:\\yml\\_myScript_\\dj_things\\web_development\\svn_views\\django_src\\trunk')
#sys.path.append('C:\\yml\\_myScript_\\dj_things\\web_development\\svn_views\\django-registration')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ispdb.apache.production")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
