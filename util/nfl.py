from bs4 import BeautifulSoup
from datetime import datetime
import urllib2

TEAM_CONVERSIONS = {
    'WSH': 'WAS'
}

def extract_team(raw):
    return TEAM_CONVERSIONS.get(raw, raw)

def get_schedule_data(week):
    schedule_url = 'http://www.espn.com/nfl/schedule/_/week/{0}'.format(week)
    return urllib2.urlopen(schedule_url).read()

    #with open(sys.argv[1], 'r') as html_file:
        #html = html_file.read()

def get_games(week):
    html = get_schedule_data(week)
    soup = BeautifulSoup(html, 'html.parser')
    schedule = soup.find_all('div', id='sched-container')[0]

    for table_body in schedule.find_all('tbody'):
        for row in table_body.find_all('tr'):
            cells = list(row.find_all('td'))
            away_team = extract_team(cells[0].text.split()[-1])
            home_team = extract_team(cells[1].text.split()[-1])
            try:
                game_time = datetime.strptime(cells[2]['data-date'],
                        '%Y-%m-%dT%H:%MZ')
            except KeyError:
                # completed games don't have this field
                continue
            yield away_team, home_team, game_time


