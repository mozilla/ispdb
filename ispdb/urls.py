from django.conf.urls import patterns, include, url
from django.http import HttpResponse
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from ispdb.config.models import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

unclaimed_dict = {
    'queryset': UnclaimedDomain.objects.all(),
}

urlpatterns = patterns('',
    (r'^robots\.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: /", mimetype="text/plain")),
    (r'^admin/', include(admin.site.urls)),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^openid/', include('django_openid_auth.urls')),
    url(r'^logout/', 'ispdb.config.views.logout_view', name='ispdb_logout'),
    url(r'^admin_login/', 'ispdb.config.views.admin_login', name="ispdb_login"),
    url(r'^$', 'ispdb.config.views.intro', name='ispdb_index'),
    url(r'^list/(?P<format>\w+)', 'ispdb.config.views.list', name='ispdb_list'),
    url(r'^list', 'ispdb.config.views.list', name='ispdb_list'),
    url(r'^details/(?P<id>\d+)', 'ispdb.config.views.details', name='ispdb_details'),
    url(r'^export_xml/(?P<id>\d+)$',
        'ispdb.config.views.export_xml', name='ispdb_export_xml'),
    url(r'^export_xml/v(?P<version>\d+\.\d+)/(?P<id>\d+)$',
        'ispdb.config.views.export_xml', name='ispdb_export_xml'),
    url(r'^export_xml/(?P<domain>[^\/]+)$',
        'ispdb.config.views.export_xml', name='ispdb_export_xml'),
    url(r'^export_xml/v(?P<version>\d+\.\d+)/(?P<domain>.+)$',
        'ispdb.config.views.export_xml', name='ispdb_export_xml'),
    url(r'^add/(?P<domain>.+)', 'ispdb.config.views.add', name='ispdb_add'),
    url(r'^add/', 'ispdb.config.views.add', name='ispdb_add'),
    url(r'^queue$', 'ispdb.config.views.queue', name='ispdb_queue'),
    url(r'^policy$', 'ispdb.config.views.policy', name='ispdb_policy'),
    url(r'^approve/(?P<id>\d+)', 'ispdb.config.views.approve', name='ispdb_approve'),
    url(r'^check_domain$', 'ispdb.config.views.check_domain',
        name='ispdb_check_domain'),
    url(r'^check_domain/(?P<name>.+)', 'ispdb.config.views.check_domain',
        name='ispdb_check_domain_name'),
)

urlpatterns += staticfiles_urlpatterns()
