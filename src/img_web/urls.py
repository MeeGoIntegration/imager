from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.generic.simple import direct_to_template
import img_web.settings as settings
# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

app_urlpatterns = patterns('',
    # Example:
    # (r'^img/', include('img.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
     (r'^admin/', include(admin.site.urls)),
    url(r'submit/$', 'img_web.app.views.submit', name='img-app-submit'), 
    url(r'queue/clear/$', 'img_web.app.views.clear', name='img-app-queue-clear'),
    url(r'queue/$', 'img_web.app.views.queue', name='img-app-queue'),
    url(r'job/(?P<msgid>\S+)$', 'img_web.app.views.job', name='img-app-job'),      
    url(r'imgs/(?P<msgid>\S+)$', 'img_web.app.views.download',name='img-app-download'),
    url(r'^login/$', 'django.contrib.auth.views.login', name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', name='logout'),

    url(r'^site_media/(?P<path>.*)$', 'django.views.static.serve',
	        {'document_root': settings.STATIC_DOC_ROOT}),
    url(r'$', 'img_web.app.views.index', name='index'),

)

urlpatterns = patterns('', (r''+settings.url_prefix+'/', include(app_urlpatterns)),)

