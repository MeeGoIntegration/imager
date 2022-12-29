from django.urls import include, path, re_path
from django.http import HttpResponse
import img_web.settings as settings
import img_web.app.views as views
from django.contrib import admin
from django.contrib.auth.views import LoginView
admin.autodiscover()

app_urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'submit/$', views.submit, name='img-app-submit'),
    re_path(r'queue/$', views.queue, name='img-app-queue'),
    re_path(r'queue/filter/$', views.queue, {'dofilter' : True}, name='img-app-queue-filter'),
    re_path(r'queue/filter/(?P<queue_name>\S+?)/$', views.queue, {'dofilter': True}, name='img-app-queue-filter-name'),
    re_path(r'queue/(?P<queue_name>\S+?)/$', views.queue, name='img-app-queue-name'),
    re_path(r'job/delete/(?P<msgid>\S+)$', views.delete_job, name='img-app-delete-job'),
    re_path(r'job/retry/(?P<msgid>\S+)$', views.retry_job, name='img-app-retry-job'),
    re_path(r'job/retest/(?P<msgid>\S+)$', views.retest_job, name='img-app-retest-job'),
    re_path(r'job/togglepin/(?P<msgid>\S+)$', views.toggle_pin_job, name='img-app-toggle-pin-job'),
    re_path(r'job/(?P<msgid>\S+)$', views.job, name='img-app-job'),
    re_path(r'search/(?P<tag>\S+)$', views.search, name='img-app-search-tag'),
    re_path(r'search/', views.search, name='img-app-search'),
#    re_path(r'^login/$', login, name='login'),
#    re_path(r'^logout/$', logout_then_login, name='logout'),
    re_path(r'$', views.index, name='index'),
    path('login/',
        LoginView.as_view(
            template_name='users/login.html'
        ),
        name="login"
    ),
]

urlpatterns = [re_path(r'^%s/' % settings.url_prefix, include(app_urlpatterns))]
