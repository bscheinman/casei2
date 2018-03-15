from bs4 import BeautifulSoup
import datetime
import urllib2

TEAM_CONVERSIONS = {
    'L-IL': 'LOY',
    'VILL': 'NOVA',
    'HALL': 'SHU',
    'GONZ': 'ZAGA',
}

GECKO_DRIVER_PATH = '/home/brendon/geckodriver'

def extract_team(raw):
    return TEAM_CONVERSIONS.get(raw, raw)

def get_schedule_data(date, driver=None):
    schedule_url = 'http://www.espn.com/mens-college-basketball/scoreboard/_/date/{year}{month:02d}{day:02d}'.format(
        year=date.year, month=date.month, day=date.day)
    if driver is None:
        options = Options()
        options.add_argument('-headless')
        driver = Firefox(executable_path=GECKO_DRIVER_PATH, firefox_options=options)

    driver.get(schedule_url)
    return driver.page_source

def get_games(date, html=None):
    if not html:
        html = get_schedule_data(date)
    soup = BeautifulSoup(html, 'html.parser')
    game_list = soup.find('div', id='events')

    for game in game_list.find_all('article'):
        date_header = game.find('th', {'class': 'date-time'})
        try:
            game_time = datetime.datetime.strptime(date_header['data-date'],
                    '%Y-%m-%dT%H:%MZ')
        except KeyError:
            # completed games don't have this field
            continue

        #team_cells = game.find_all('span', {'class': 'sb-team-short'})
        team_cells = game.find_all('span', {'class': 'sb-team-abbrev'})
        if len(team_cells) != 2:
            continue

        away_team = extract_team(team_cells[0].text)
        home_team = extract_team(team_cells[1].text)

        yield away_team, home_team, game_time
