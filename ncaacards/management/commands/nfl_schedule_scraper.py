from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils.timezone import make_aware
from ncaacards.models import GameType, LiveGame, Team
from util import nfl

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('week', nargs=1, type=int)

    def add_game(self, game_type, away, home, game_time):
        away_team = Team.objects.get(game_type=game_type, abbrev_name=away)
        home_team = Team.objects.get(game_type=game_type, abbrev_name=home)
        game_time = make_aware(game_time)

        # later in the season some games get moved around
        # one good way to identify duplicates and update them would be to
        # explicitly tag each game with its week, but checking +/- one day is
        # probably a good enough heuristic.
        # same calendar day won't work because UTC sometimes pushes times across
        # days.
        min_time = game_time - timedelta(days=1)
        max_time = game_time + timedelta(days=1)

        try:
            existing = LiveGame.objects.get(home_team=home_team,
                    away_team=away_team, game_time__gt=min_time,
                    game_time__lt=max_time)

            if existing.game_time != game_time:
                print 'updating {0} time to {1}'.format(existing, game_time)
                existing.game_time = game_time
                existing.save()
            else:
                print '{0} unchanged'.format(existing)
        except LiveGame.DoesNotExist:
            new_game = LiveGame.objects.create(home_team=home_team,
                    away_team=away_team, game_time=game_time)
            print 'created new game {0}'.format(new_game)

    def handle(self, *args, **options):
        game_type = GameType.objects.get(name='NFL 2017')
        for away, home, game_time in nfl.get_games(options['week']):
            self.add_game(game_type, away, home, game_time)
