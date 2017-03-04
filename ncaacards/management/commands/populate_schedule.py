from casei.ncaacards.models import GameType, LiveGame, Team
from django.core.management.base import NoArgsCommand
import datetime
import json
import re
import urllib2


class Command(NoArgsCommand):
    
    team_names = {
        'Arizona Diamondbacks' : 'ARZ',
        'Atlanta Braves' : 'ATL',
        'Baltimore Orioles' : 'BAL',
        'Boston Red Sox' : 'BOS',
        'Chicago Cubs' : 'CHC',
        'Chicago White Sox' : 'CHW',
        'Cincinnati Reds' : 'CIN',
        'Cleveland Indians' : 'CLE',
        'Colorado Rockies' : 'COL',
        'Detroit Tigers' : 'DET',
        'Houston Astros' : 'HOU',
        'Kansas City Royals' : 'KC',
        'LA Angels' : 'LAA',
        'LA Dodgers' : 'LAD',
        'Florida Marlins' : 'MIA',
        'Miami Marlins' : 'MIA',
        'Milwaukee Brewers' : 'MIL',
        'Minnesota Twins' : 'MIN',
        'NY Mets' : 'NYM',
        'NY Yankees' : 'NYY',
        'Oakland A\'s' : 'OAK',
        'Philadelphia Phillies' : 'PHI',
        'Pittsburgh Pirates' : 'PIT',
        'SD Padres' : 'SD',
        'Seattle Mariners' : 'SEA',
        'SF Giants' : 'SF',
        'St Louis Cardinals' : 'STL',
        'Tampa Bay Rays' : 'TB',
        'Texas Rangers' : 'TEX',
        'Toronto Blue Jays' : 'TOR',
        'Washington Nationals' : 'WAS',
    }
    game_desc_regex = re.compile('(?P<away>[A-Za-z\' ]+) @ (?P<home>[A-Za-z\' ]+)')
    fanfeedr_url = 'http://ffapi.fanfeedr.com/basic/api/leagues/20f0857f-3c43-5f50-acfc-879f838ee853/events/today?api_key=p3q9e2t5tess5z55jdved5nm'
    game_type = GameType.objects.get(name='MLB')

    def get_team(self, team_name):
        return Team.objects.get(game_type=self.game_type, abbrev_name=self.team_names[team_name])

    def handle_noargs(self, **options):
        for result in json.loads(urllib2.urlopen(self.fanfeedr_url).read()):
            game_desc = self.game_desc_regex.match(result['name']).groupdict()
            try:
                game_time = datetime.datetime.strptime(result['date'], '%Y-%m-%dT%H:%M:%S.%fZ')
                home_team, away_team = self.get_team(game_desc['home']), self.get_team(game_desc['away'])
                LiveGame.objects.create(home_team=home_team, away_team=away_team, game_time=game_time)
            except:
                pass
