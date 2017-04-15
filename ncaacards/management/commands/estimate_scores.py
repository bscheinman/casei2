from ncaacards.models import GameTeam
from trading.models import Security
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        for game_team in GameTeam.objects.all().select_related('game', 'team'):
            # should probably batch this but this is intended as a one-time migration script, so meh
            security = Security.objects.filter(market__name=game_team.game.name, name=game_team.team.abbrev_name)[0]
            game_team.update_estimated_score(security)
