import requests
import csv
import json
import sys
import time
from datetime import datetime

s = requests.Session()

# get IGDB creds
with open('backloggd.json', 'r') as f:
    j = json.loads(f.read())

id = j['id']
secret = j['secret']
backloggd_id = j['backloggd_id']
backloggd_csrf = j['csrf']
backloggd_cookie = j['cookie']

access_url = 'https://id.twitch.tv/oauth2/token?client_id=%s&client_secret=%s&grant_type=client_credentials' % (
    id, secret)
r = s.post(access_url)
response = json.loads(r.text)

access_token = response['access_token']
expires = int(response['expires_in'])
endpoint = 'https://api.igdb.com/v4/games/'
headers = {'Client-ID': id, 'Authorization': 'Bearer ' + access_token}

BACKLOGGD_HEADERS = {
    'Connection': 'keep-alive',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="90", "Google Chrome";v="90"',
    'Accept': '*/*',
    'X-CSRF-Token': '',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'https://www.backloggd.com',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Dest': 'empty',
    'Referer': 'https://www.backloggd.com/',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cookie': '',
}


def update_cookie(session):
    BACKLOGGD_HEADERS['Cookie'] = "ne_cookies_consent=true; _backloggd_session=" + session


def update_csrf(key):
    BACKLOGGD_HEADERS['X-CSRF-Token'] = key


def get_game_id(name, platform):
    try:
        body = 'fields name; search "%s"; where platforms = (%s);' % (
            name, platform)
        r = s.post(endpoint, headers=headers, data=body)
        j = json.loads(r.text)
        actual_game = [g['id'] for g in j]
        if len(actual_game) > 0:
            return actual_game[0]  # this is the ID
        else:
            return None  # game not found
    except:
        print("Error getting game id " + name)
        return None


def get_plaform_id():
    platforms_endpont = 'https://api.igdb.com/v4/platforms'
    try:
        body = 'fields name; limit 300;'
        r = s.post(platforms_endpont, headers=headers, data=body)
        j = json.loads(r.text)
        if len(j) > 0:
            return j  # this is the ID
        else:
            return None  # game not found
    except:
        print("Error getting platform names")
        return None


def add_game(game_id, rating, platform, is_play, is_playing, is_backlog, is_wishlist, status):
    data = {
        'game_id': game_id,
        'playthroughs[0][id]': -1,
        'playthroughs[0][title]': 'Log',
        'playthroughs[0][rating]': rating,
        'playthroughs[0][review]': '',
        'playthroughs[0][review_spoilers]': 'false',
        'playthroughs[0][platform]': platform,
        'playthroughs[0][hours]': '',
        'playthroughs[0][minutes]': '',
        'playthroughs[0][is_master]': 'false',
        'playthroughs[0][is_replay]': 'false',
        'playthroughs[0][start_date]': '',
        'playthroughs[0][finish_date]': '',
        'log[is_play]': is_play,
        'log[is_playing]': is_playing,
        'log[is_backlog]': is_backlog,
        'log[is_wishlist]': is_wishlist,
        # played, completed (default), retired, shelved, abandoned
        'log[status]': status,
        'log[id]': '',
        'modal_type': 'quick'
    }
    backloggd_url = 'https://www.backloggd.com/api/user/' + \
        str(backloggd_id) + '/log/' + str(game_id)
    add_request = s.post(backloggd_url, headers=BACKLOGGD_HEADERS, params=data)
    return add_request.status_code


# Match game names to IGDB IDs, submit to backloggd
# Games with no IDs will be written to text file notfound.txt
update_cookie(backloggd_cookie)
update_csrf(backloggd_csrf)
platforms = get_plaform_id()
not_found_games = open('notfound.txt', 'w')
start_from_row = 1
index = 0
with open('games.csv', 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    for row in reader:
        if index < start_from_row:
            index += 1
            continue
        name = row[0]
        platform_name = row[1]
        is_play = row[2]
        is_playing = row[3]
        is_backlog = row[4]
        is_wishlist = row[5]
        status = row[6]
        rating = row[7]
        trying = True
        while trying:
            platform = next(i for i in platforms if i['name'] == platform_name)
            game_id = get_game_id(name, platform['id'])
            if game_id is not None:
                status = add_game(
                    game_id, rating, platform['id'], is_play, is_playing, is_backlog, is_wishlist, status)
                trying = False
                if status < 400:
                    print('Added ' + name)
                elif status == 429:
                    print('Hit request limit, pausing')
                    trying = True  # try again
                    time.sleep(60*3)
                    print('Trying again')
                else:
                    print('Game already added or headers error ' + name)
            else:
                not_found_games.write(','.join(row) + '\n')
                trying = False
not_found_games.close()
