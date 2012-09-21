from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.generic.simple import direct_to_template
import img_web.settings as settings
from django.contrib import admin
admin.autodiscover()

app_urlpatterns = patterns('',
     (r'^admin/', include(admin.site.urls)),
    url(r'submit/$', 'img_web.app.views.submit', name='img-app-submit'), 
    url(r'queue/$', 'img_web.app.views.queue', name='img-app-queue'),
    url(r'queue/filter/$', 'img_web.app.views.queue', {'dofilter' : True}, name='img-app-queue-filter'),
    url(r'queue/filter/(?P<queue_name>\S+?)/$', 'img_web.app.views.queue', {'dofilter': True}, name='img-app-queue-filter-name'),
    url(r'queue/(?P<queue_name>\S+?)/$', 'img_web.app.views.queue', name='img-app-queue-name'),
    url(r'job/delete/(?P<msgid>\S+)$', 'img_web.app.views.delete_job', name='img-app-delete-job'),
    url(r'job/retry/(?P<msgid>\S+)$', 'img_web.app.views.retry_job', name='img-app-retry-job'),
    url(r'job/retest/(?P<msgid>\S+)$', 'img_web.app.views.retest_job', name='img-app-retest-job'),
    url(r'job/togglepin/(?P<msgid>\S+)$', 'img_web.app.views.toggle_pin_job', name='img-app-toggle-pin-job'),
    url(r'job/(?P<msgid>\S+)$', 'img_web.app.views.job', name='img-app-job'),
    url(r'search/(?P<tag>\S+)$', 'img_web.app.views.search', name='img-app-search-tag'),
    url(r'search/', 'img_web.app.views.search', name='img-app-search'),
    url(r'^login/$', 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name='logout'),

    #url(r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
	#        {'document_root': settings.STATIC_ROOT}),
    url(r'$', 'img_web.app.views.index', name='index'),

)

urlpatterns = patterns('', (r''+settings.url_prefix+'/', include(app_urlpatterns)),)

