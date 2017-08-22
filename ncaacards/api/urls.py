from django.conf.urls import url, include
from ncaacards.api import views

urlpatterns = [
    url(r'^make_market$', views.make_market),
    url(r'^positions$', views.positions),
    url(r'^executions$', views.executions),
    url(r'^open_orders$', views.open_orders),
    url(r'^cancel_order$', views.cancel_order),
    url(r'^place_order$', views.place_order),
    url(r'^my_markets$', views.my_markets),
    url(r'^market_data$', views.market_data),
    url(r'^get_book$', views.get_book),
]
