from django.conf.urls import url, include

from ncaacards import views
from ncaacards.feeds import RecentCardTradesFeed, RecentStockTradesFeed

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = [
    url(r'^$', views.home),
#    url(r'^game/([0-9]+)/$', 'casei.ncaacards.views.game_home'),
#    url(r'^game/([0-9]+)/rss/cards/$', RecentCardTradesFeed()),
#    url(r'^game/([0-9]+)/rss/stocks/$', RecentStockTradesFeed()),
#    url(r'^game/([0-9]+)/scoring_settings/$', 'casei.ncaacards.views.scoring_settings'),
#    url(r'^game/([0-9]+)/save_settings/$', 'casei.ncaacards.views.save_settings'),
#    url(r'^game/([0-9]+)/lock_settings/$', 'casei.ncaacards.views.lock_settings'),
#    url(r'^game/([0-9]+)/marketplace/$', 'casei.ncaacards.views.marketplace'),
#    url(r'^game/([0-9]+)/team_list/$', 'casei.ncaacards.views.team_list'),
#    url(r'^game/([0-9]+)/market_maker/$', 'casei.ncaacards.views.market_maker'),
#    url(r'^game/([0-9]+)/make_market/$', 'casei.ncaacards.views.do_make_market'),
#    url(r'^game/([0-9]+)/leaderboard/$', 'casei.ncaacards.views.leaderboard'),
#    url(r'^game/([0-9]+)/entry/([0-9]+)/$', 'casei.ncaacards.views.entry_view'),
#    url(r'^game/([0-9]+)/team/([0-9]+)/$', 'casei.ncaacards.views.game_team_view'),
#    url(r'^game/([0-9]+)/team/([a-zA-Z]+)/$', 'casei.ncaacards.views.game_team_view'),
#    url(r'^game/([0-9]+)/create_offer/$', 'casei.ncaacards.views.create_offer'),
#    url(r'^game/([0-9]+)/make_offer/$', 'casei.ncaacards.views.make_offer'),
#    url(r'^game/([0-9]+)/place_order/$', 'casei.ncaacards.views.do_place_order'),
#    url(r'^game/([0-9]+)/cancel_order/$', 'casei.ncaacards.views.cancel_order'),
#    url(r'^game/([0-9]+)/change_order/$', 'casei.ncaacards.views.change_order'),
#    url(r'^game/([0-9]+)/offer/([0-9]+)/$', 'casei.ncaacards.views.offer_view'),
#    url(r'^game/([0-9]+)/offer/([0-9]+)/accept/$', 'casei.ncaacards.views.accept_offer'),
#    url(r'^game/([0-9]+)/offer/([0-9]+)/cancel/$', 'casei.ncaacards.views.cancel_offer'),
#    url(r'^create_game/$', 'casei.ncaacards.views.create_game'),
#    url(r'^game_list/$', 'casei.ncaacards.views.game_list'),
#    url(r'^do_create_game/$', 'casei.ncaacards.views.do_create_game'),
#    url(r'^join_game/$', 'casei.ncaacards.views.join_game'),
]
