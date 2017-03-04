from ncaacards.models import GameTeam, NcaaGame, TradeOffer
from trading.models import Execution
from django.contrib.syndication.views import Feed
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.feedgenerator import Rss201rev2Feed

class RecentStockTradesFeed(Feed):
    feed_type = Rss201rev2Feed
    
    def get_object(self, request, game_id):
        return get_object_or_404(NcaaGame, pk=game_id)


    def title(self, game):
        return 'Recent Stock Trades in %s' % game.name


    def link(self, game):
        return 'http://caseinsensitive.org/ncaa/game/%s/' % game.id


    def item_link(self, trade):
        try:
            game_team = GameTeam.objects.get(game__name=trade.security.market.name, team__abbrev_name=trade.security.name)
            return 'http://caseinsensitive.org/ncaa/game/%s/team/%s/?start_tab=stock_tab' % (game_team.game.id, game_team.team.abbrev_name)
        except GameTeam.DoesNotExist:
            return 'http://caseinsensitive.org/ncaa/'
    

    def description(self, game):
        return 'Stock trades recently completed in game %s' % game.name


    def items(self, game):
        return Execution.objects.filter(security__market__name=game.name).order_by('-time')[:50]


class RecentCardTradesFeed(Feed):
    feed_type = Rss201rev2Feed
    
    def get_object(self, request, game_id):
        return get_object_or_404(NcaaGame, pk=game_id)


    def title(self, game):
        return 'Recent Card Trades in %s' % game.name


    def link(self, game):
        return 'http://caseinsensitive.org/ncaa/game/%s/' % game.id


    def item_link(self, trade):
        return 'http://caseinsensitive.org/ncaa/game/%s/offer/%s/' % (trade.entry.game.id, trade.id)
    

    def description(self, game):
        return 'Card trades recently completed in game %s' % game.name


    def items(self, game):
        return TradeOffer.objects.filter(Q(entry__game=game) & ~Q(accepting_user=None)).order_by('-accept_time')[:25]
