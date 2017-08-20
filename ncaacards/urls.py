from django.conf.urls import url, include

from ncaacards import views
from ncaacards.feeds import RecentCardTradesFeed, RecentStockTradesFeed

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = [
    url(r'^api/', include('ncaacards.api.urls')),
    url(r'^$', views.home),
    url(r'^game/([0-9]+)/$', views.game_home),
    url(r'^game/([0-9]+)/rss/cards/$', RecentCardTradesFeed()),
    url(r'^game/([0-9]+)/rss/stocks/$', RecentStockTradesFeed()),
    url(r'^game/([0-9]+)/scoring_settings/$', views.scoring_settings),
    url(r'^game/([0-9]+)/save_settings/$', views.save_settings),
    url(r'^game/([0-9]+)/lock_settings/$', views.lock_settings),
    url(r'^game/([0-9]+)/marketplace/$', views.marketplace),
    url(r'^game/([0-9]+)/team_list/$', views.team_list),
    url(r'^game/([0-9]+)/market_maker/$', views.market_maker),
    url(r'^game/([0-9]+)/make_market/$', views.do_make_market),
    url(r'^game/([0-9]+)/leaderboard/$', views.leaderboard),
    url(r'^game/([0-9]+)/entry/([0-9]+)/$', views.entry_view),
    url(r'^game/([0-9]+)/team/([0-9]+)/$', views.game_team_view),
    url(r'^game/([0-9]+)/team/([a-zA-Z]+)/$', views.game_team_view),
    url(r'^game/([0-9]+)/create_offer/$', views.create_offer),
    url(r'^game/([0-9]+)/make_offer/$', views.make_offer),
    url(r'^game/([0-9]+)/place_order/$', views.do_place_order),
    url(r'^game/([0-9]+)/cancel_order/$', views.cancel_order),
    url(r'^game/([0-9]+)/change_order/$', views.change_order),
    url(r'^game/([0-9]+)/offer/([0-9]+)/$', views.offer_view),
    url(r'^game/([0-9]+)/offer/([0-9]+)/accept/$', views.accept_offer),
    url(r'^game/([0-9]+)/offer/([0-9]+)/cancel/$', views.cancel_offer),
    url(r'^create_game/$', views.create_game),
    url(r'^game_list/$', views.game_list),
    url(r'^do_create_game/$', views.do_create_game),
    url(r'^join_game/$', views.join_game),
]
