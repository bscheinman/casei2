from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.contrib.auth import views as auth_views

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
    url(r'^password_reset/$', auth_views.PasswordResetView.as_view() , {
        'post_reset_redirect': '/password_reset_sent/',
    }, name='password_reset'),
    url(r'^password_reset_sent/$', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    url(r'^password_reset_complete/$', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,32})/$',
        auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    url(r'^yodawg/', admin.site.urls),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
