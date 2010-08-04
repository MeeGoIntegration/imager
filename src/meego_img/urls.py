from django.conf.urls.defaults import *
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.views.generic.simple import direct_to_template
from meego_img import settings
# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^img/', include('img.foo.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
    url(r'submit/$', 'meego_img.app.views.submit', name='img-app-submit'), 
    url(r'queue/$', 'meego_img.app.views.queue', name='img-app-queue'),
    #(r'$', 'meego_img.app.views.index'),
    url(r'job/(?P<msgid>\S+)$', 'meego_img.app.views.job', name='img-app-job'),      
    url(r'images/(?P<msgid>\S+)$', 'meego_img.app.views.download',name='img-app-download'),
)
