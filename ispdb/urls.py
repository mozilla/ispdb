from django.conf.urls import patterns, include, url
from django.http import HttpResponse
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from ispdb.config.models import *

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^robots\.txt$', lambda r: HttpResponse("User-agent: *\nDisallow: /", mimetype="text/plain")),
    (r'^admin/', include(admin.site.urls)),
    (r'^comments/post/', 'ispdb.config.views.comment_post_wrapper'),
    url(r'^comments/delete/(\d+)/$', 'ispdb.config.views.delete_comment',
        name='ispdb_comment_delete'),
    (r'^comments/', include('django.contrib.comments.urls')),
    (r'^browserid/', include('django_browserid.urls')),
    url(r'^login/$', 'ispdb.config.views.login', name='ispdb_login'),
    url(r'^logout/', 'ispdb.config.views.logout_view', name='ispdb_logout'),
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
    url(r'^add/(?P<domain>[\w\d\-\.]+)/?$', 'ispdb.config.views.add',
        name='ispdb_add'),
    url(r'^add/', 'ispdb.config.views.add', name='ispdb_add'),
    url(r'^edit/(?P<config_id>\d+)/?$', 'ispdb.config.views.edit',
        name='ispdb_edit'),
    url(r'^queue$', 'ispdb.config.views.queue', name='ispdb_queue'),
    url(r'^policy$', 'ispdb.config.views.policy', name='ispdb_policy'),
    url(r'^approve/(?P<id>\d+)', 'ispdb.config.views.approve', name='ispdb_approve'),
    url(r'^delete/(?P<id>\d+)/?', 'ispdb.config.views.delete',
        name='ispdb_delete'),
    url(r'^report/(?P<id>\d+)', 'ispdb.config.views.report', name='ispdb_report'),
    url(r'^show_issue/(?P<id>\d+)', 'ispdb.config.views.show_issue',
        name='ispdb_show_issue'),
)

urlpatterns += staticfiles_urlpatterns()
