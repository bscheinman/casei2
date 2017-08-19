from django.conf.urls import url, include
from ncaacards.api import views

urlpatterns = [
    url(r'^make_market$', views.make_market),
    url(r'^positions$', views.positions),
    url(r'^executions$', views.executions),
    url(r'^open_orders$', views.open_orders),
    url(r'^cancel_order$', views.cancel_order),
]
