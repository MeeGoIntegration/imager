from django.conf.urls import include, url
from django.http import HttpResponse
from django.shortcuts import render_to_response
import img_web.settings as settings
import img_web.app.views as views
from django.contrib import admin
from django.contrib.auth.views import login, logout_then_login
admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'submit/$', views.submit, name='img-app-submit'), 
    url(r'queue/$', views.queue, name='img-app-queue'),
    url(r'queue/filter/$', views.queue, {'dofilter' : True}, name='img-app-queue-filter'),
    url(r'queue/filter/(?P<queue_name>\S+?)/$', views.queue, {'dofilter': True}, name='img-app-queue-filter-name'),
    url(r'queue/(?P<queue_name>\S+?)/$', views.queue, name='img-app-queue-name'),
    url(r'job/delete/(?P<msgid>\S+)$', views.delete_job, name='img-app-delete-job'),
    url(r'job/retry/(?P<msgid>\S+)$', views.retry_job, name='img-app-retry-job'),
    url(r'job/retest/(?P<msgid>\S+)$', views.retest_job, name='img-app-retest-job'),
    url(r'job/togglepin/(?P<msgid>\S+)$', views.toggle_pin_job, name='img-app-toggle-pin-job'),
    url(r'job/(?P<msgid>\S+)$', views.job, name='img-app-job'),
    url(r'search/(?P<tag>\S+)$', views.search, name='img-app-search-tag'),
    url(r'search/', views.search, name='img-app-search'),
    url(r'^login/$', login, name='login'),
    url(r'^logout/$', logout_then_login, name='logout'),
    url(r'$', views.index, name='index'),
]


