import traceback
import requests
import csv
import json
import sys
import time
from datetime import datetime, timedelta

s = requests.Session()

# get IGDB creds
with open('backloggd.json', 'r') as f:
    j = json.loads(f.read())

id = j['id']
secret = j['secret']
backloggd_id = j['backloggd_id']
backloggd_csrf = j['csrf']
backloggd_cookie = j['cookie']

access_url = f'https://id.twitch.tv/oauth2/token?client_id={id}&client_secret={secret}&grant_type=client_credentials'
r = s.post(access_url)
response = json.loads(r.text)

access_token = response['access_token']
expires = int(response['expires_in'])
endpoint = 'https://api.igdb.com/v4/games/'
headers = {'Client-ID': id, 'Authorization': 'Bearer ' + access_token}

BACKLOGGD_HEADERS = {
    "accept": "*/*",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "no-cache",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "pragma": "no-cache",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Google Chrome\";v=\"136\", \"Vivaldi\";v=\"7.4\", \"Not.A/Brand\";v=\"99\", \"Chromium\";v=\"136\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-csrf-token": backloggd_csrf,
    "x-requested-with": "XMLHttpRequest"
}

cookies = {
    'ne_cookies_consent': 'true',
    '_backloggd_session': backloggd_cookie,
}


def get_game_id(name, platform):
    time.sleep(0.5)
    try:
        body = f'fields name; search "{name}"; where platforms = ({platform});'
        r = s.post(endpoint, headers=headers, data=body)
        j = json.loads(r.text)

        if 'message' in j:
            print(j['message'])
            print('Waiting...')
            time.sleep(5)   
            return (None, None)
        
        if len(j) == 0:
            return (None, None)
        
        if 'status' in j[0]:
            print(f'{name}: {j}')
            return (None, None)
        
        return (j[0]['id'], j[0]['name'])
    except Exception:
        traceback.print_exc()
        return (None, None)


def get_platform_ids():
    platforms_endpont = 'https://api.igdb.com/v4/platforms'
    try:
        body = 'fields name; limit 300;'
        r = s.post(platforms_endpont, headers=headers, data=body)
        j = json.loads(r.text)
        if len(j) == 0:
            print("Error getting platform names")
            return None
        return {x['name']: x['id'] for x in j}
    except:
        print("Error getting platform names")
        return None


def add_game(game_id, rating, platform_id, status, time_completed, review, **kwargs):
    completed = datetime.strptime(time_completed, "%B %d, %Y %I:%M %p")
    start = completed - timedelta(days=1)
    skip_time = completed <= datetime(2021, 11, 12)
    data = {
        'game_id': game_id,
        'playthroughs[0][id]': -1,
        'playthroughs[0][title]': 'Log',
        'playthroughs[0][rating]': rating,
        'playthroughs[0][review]': review,
        'playthroughs[0][review_spoilers]': 'false',
        'playthroughs[0][platform]': platform_id,
        'playthroughs[0][hours_played]': '',
        'playthroughs[0][mins_played]': '',
        'playthroughs[0][sync_sessions]': 'true',
        'playthroughs[0][is_master]': 'false',
        'playthroughs[0][is_replay]': 'false',
        'playthroughs[0][start_date]': '',
        'playthroughs[0][finish_date]': completed.strftime("%Y-%m-%d") if not skip_time else '',
        'playthroughs[0][edition_id]': '',
        'playthroughs[0][medium_id]': '',
        'playthroughs[0][played_platform]': '',
        'playthroughs[0][storefront_id]': '',
        'playthroughs[0][hours_finished]': '',
        'playthroughs[0][mins_finished]': '',
        'playthroughs[0][hours_mastered]': '',
        'playthroughs[0][mins_mastered]': '',
        'log[game_liked]': 'false',
        'log[is_play]': 'true',
        'log[is_playing]': 'false',
        'log[is_backlog]': 'false',
        'log[is_wishlist]': 'false',
        # played, completed (default), retired, shelved, abandoned
        'log[status]': status,
        'log[id]': '',
        'log[total_hours]': '',
        'log[total_minutes]': '',
        'log[time_source]': '0',
        'modal_type': 'full'
    }

    if not skip_time:
        data.update({
            'dates[-1][0][id]': '-1',
            'dates[-1][0][range_start_date]': start.strftime("%Y-%m-%d"),
            'dates[-1][0][range_end_date]': completed.strftime("%Y-%m-%d"),
            'dates[-1][0][edited]': 'true',
            'dates[-1][0][status]': '5',
            'dates[-1][0][note]': '',
            'dates[-1][0][hours]': '',
            'dates[-1][0][minutes]': '',
            'dates[-1][0][start_date]': '',
            'dates[-1][0][finish_date]': completed.strftime("%Y-%m-%d"),
        })

    backloggd_url = f'https://backloggd.com/api/user/{backloggd_id}/log/{game_id}'
    add_request = s.post(backloggd_url, headers=BACKLOGGD_HEADERS, data=data, cookies=cookies)
    return add_request.status_code


def write_out_csv(games):
    with open('games.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(games)


platforms = get_platform_ids()

games = {}
fieldnames = []
unknown_platforms = set()
unknown_games = set()

with open('games.csv', 'r') as csvfile:
    games_reader = csv.DictReader(csvfile)
    if 'platform_id' not in games_reader.fieldnames:
        games_reader.fieldnames.append('platform_id')
    if 'game_id' not in games_reader.fieldnames:
        games_reader.fieldnames.append('game_id')
    if 'found_name' not in games_reader.fieldnames:
        games_reader.fieldnames.append('found_name')
    if 'uploaded' not in games_reader.fieldnames:
        games_reader.fieldnames.append('uploaded')
    fieldnames = list(games_reader.fieldnames)
    games = list(games_reader)

# try and find the platform first
for row in games:
    platform = row['platform']
    platform_id = platforms[platform] if platform in platforms else None
    if platform_id is None:
        unknown_platforms.add(platform)
        continue

    row['platform_id'] = platform_id

# bail if any platforms are bad
if len(unknown_platforms) > 0:
    for p in sorted(platforms.keys()):
        print(p)
    print(f'unknown platforms: {list(unknown_platforms)}')

    write_out_csv(games)
    sys.exit(-1)

# now figure out game ids for everything
for row in [x for x in games if x['game_id'] == '']:
    name = row['name']
    platform_id = row['platform_id']

    (game_id, game_name) = get_game_id(name, platform_id)
    if game_id is None:
        unknown_games.add(name)
        continue
    else:
        row['game_id'] = game_id
        row['found_name'] = game_name

# bail if any games are unknown, and let them know which ones
if len(unknown_games) > 0:
    for game in unknown_games:
        print(game)
    write_out_csv(games)
    sys.exit(-1)

# now we're ready to post to backloggd!
for game in reversed([x for x in games if x['uploaded'] == '']):
    while True:
        status = add_game(**game)
        trying = False
        if status < 400:
            print('Added ' + game['name'])
            game['uploaded'] = True
            write_out_csv(games)
            break
        elif status == 429:
            print('Hit request limit, pausing')
            trying = True  # try again
            time.sleep(10)
            print('Trying again')
        else:
            print('Game already added or headers error ' + game['name'])
            break