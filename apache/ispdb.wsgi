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

os.environ['DJANGO_SETTINGS_MODULE'] = 'ispdb.apache.production'
import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()

