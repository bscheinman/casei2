from django.conf.urls import url, include
from django.contrib import admin

from cix import views

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

urlpatterns = [
    url(r'^$', views.home, name='home'),
    url(r'^login/$', views.login_page),
    url(r'^do_login/$', views.do_login),
    url(r'^signup/$', views.signup),
    url(r'^do_signup/$', views.do_signup),
    url(r'^signup_thanks/$', views.signup_thanks),
    url(r'^do_logout/$', views.do_logout),
    url(r'^verify/([a-zA-Z0-9]+)/$', views.verify),
    url(r'^ncaa/', include('ncaacards.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^yodawg/', admin.site.urls),
]
