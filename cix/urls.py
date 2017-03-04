from django.conf.urls import url, include
from django.contrib import admin

from cix import views

# Uncomment the next two lines to enable the admin:
admin.autodiscover()

urlpatterns = [
    url(r'^$', views.home, name='home'),
    #url(r'^login/$', 'cix.views.login_page'),
    #url(r'^do_login/$', 'cix.views.do_login'),
    #url(r'^signup/$', 'cix.views.signup'),
    #url(r'^do_signup/$', 'cix.views.do_signup'),
    #url(r'^signup_thanks/$', 'cix.views.signup_thanks'),
    #url(r'^do_logout/$', 'cix.views.do_logout'),
    #url(r'^verify/([a-zA-Z0-9]+)/$', 'cix.views.verify'),
    url(r'^ncaa/', include('ncaacards.urls')),
    # Examples:
    # url(r'^$', 'cix.views.home', name='home'),
    # url(r'^cix/', include('casei.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^yodawg/', admin.site.urls),
]
