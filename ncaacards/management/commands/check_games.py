from ncaacards.models import LiveGame, TradeOffer
from trading.models import Order
from django.core.management.base import BaseCommand
from django.db.models import Q
import datetime


class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        now = datetime.datetime.now()
        started_games = LiveGame.objects.filter(game_time__lt=now, is_processed=False)
        for game in started_games:
            teams = (game.home_team, game.away_team)
            #team_names = (game.home_team.abbrev_name, game.away_team.abbrev_name)
            for order in Order.open_orders.filter(security__team__team__in=teams, cancel_on_game=True):
                order.is_active = False
                order.save()
            offer_query = (Q(bid_side__components__team__team__in=teams) | Q(ask_side__components__team__team__in=teams))\
                & Q(cancel_on_game=True, is_active=True)
            for offer in TradeOffer.objects.filter(offer_query):
                offer.is_active = False
                offer.save()
            game.is_processed = True
            game.save()
