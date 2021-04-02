from datetime import timedelta

from django.core.management.base import BaseCommand
from ncaacards.models import GameType, Team, TeamScoreCount
from util import nfl

class Command(BaseCommand):
    def update_totals(self, game_type, team, wins, losses, ties):
        team_obj = Team.objects.get(game_type=game_type, abbrev_name=team)

        win_total = TeamScoreCount.objects.get(team=team_obj,
                scoreType__name='Regular Season Win')
        tie_total = TeamScoreCount.objects.get(team=team_obj,
                scoreType__name='Regular Season Tie')

        win_total.count = wins
        tie_total.count = ties

        print('updated {0} to {1} wins and {2} ties'.format(team, wins, ties))

        win_total.save()
        tie_total.save()

    def handle(self, *args, **options):
        game_type = GameType.objects.get(name='NFL 2017')
        for team, wins, losses, ties in nfl.get_standings():
            self.update_totals(game_type, team, wins, losses, ties)
