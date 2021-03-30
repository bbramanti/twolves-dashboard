import pandas as pd
import time
import logging
import datetime
from nba_api.stats.static import teams
from nba_api.stats.endpoints import boxscoretraditionalv2, teamgamelog
from dateutil.parser import parse

# configure logger
logging.basicConfig(level=logging.INFO)

# log to signal beginning of function execution
logging.info("BEGINNING CALL_NBA_API JOB AT {}".format(datetime.datetime.now()))

# get all teams data
teams_data = teams.get_teams()

# get Minnesota Timberwolves Team ID
minnesota_timberwolves_id = [team for team in teams_data if team['abbreviation'] == 'MIN'][0]['id']

# using Team ID pull all games from 2020-2021 Season
timberwolves_games_2020_2021 = teamgamelog.TeamGameLog(
    team_id = minnesota_timberwolves_id,
    season = '2020'
).get_data_frames()[0]

# select only neccessary data
timberwolves_games_2020_2021 = timberwolves_games_2020_2021[['Game_ID', 'GAME_DATE', 'MATCHUP', 'WL']]

# fix column names
timberwolves_games_2020_2021.rename(
    columns={
        'Team_ID': "TEAM_ID",
        'Game_ID': 'GAME_ID'
    },
    inplace=True
)

# change date column format from MAR 15, 2021 -> 3/15/2021
timberwolves_games_2020_2021['GAME_DATE'] = timberwolves_games_2020_2021.apply(lambda row : parse(row['GAME_DATE']).strftime('%m/%d/%Y'), axis = 1)

# sort by game date instead of game date because date would require parsing back to datetime object
timberwolves_games_2020_2021.sort_values(by=['GAME_ID'], inplace=True)

# create Dataframe to hold BoxScore data
boxscores = pd.DataFrame()

# pull each game and append results to dataframe
for index, game in timberwolves_games_2020_2021.iterrows():
    logging.info("pulling {} from {} with id {}".format(game['MATCHUP'], game['GAME_DATE'], game['GAME_ID']))
    game_instance = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id = game['GAME_ID']).get_data_frames()[0]
    boxscores = boxscores.append(game_instance)
    time.sleep(5)

# remove any records for the opposing team, or players who did not log any minutes
boxscores = boxscores[
    (boxscores['TEAM_ID'] == minnesota_timberwolves_id) &
    (boxscores['MIN'].isnull() == False)
]

# adjust MIN column -> 23:05 to 23, 23:55 to 24
def fix_minutes_played(row):
    minutes = int(row['MIN'].split(":")[0])
    seconds = int(row['MIN'].split(":")[1])
    seconds += (minutes * 60)
    return round(seconds / 60)

boxscores['MIN'] = boxscores.apply(lambda row : fix_minutes_played(row), axis = 1)

# merge BoxScore with Games data to get date/matchup/win-loss
boxscores = boxscores.merge(timberwolves_games_2020_2021, on='GAME_ID', how='left')

# drop columns that are no longer needed
boxscores.drop(
    ['GAME_ID', 'TEAM_ID', 'TEAM_CITY', 'PLAYER_ID', 'START_POSITION', 'COMMENT', 'FG_PCT', 'FG3_PCT', 'FT_PCT'],
    axis=1,
    inplace=True
)

# fix column header names
boxscores.rename(
    columns={
        'PLAYER_NAME': 'PLAYER',
        'TEAM_ABBREVIATION': 'TEAM',
        'GAME_DATE': 'DATE',
        'WL': 'W/L',
        'FG3M': '3PM',
        'FG3A': '3PA',
        'TO': 'TOV',
        'PLUS_MINUS': 'PLUS-MINUS'
    },
    inplace=True
)

# convert float columns to int
filter_columns = ['PTS', 'FGM', 'FGA', '3PM', '3PA', 'FTM', 'FTA', 'OREB', 'DREB', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'PF', 'PLUS-MINUS']
boxscores[filter_columns] = boxscores[filter_columns].astype(int)

# fix ordering of columns
column_names = [
    'PLAYER', 'TEAM', 'DATE', 'MATCHUP', 'W/L',
    'MIN', 'PTS', 'FGM', 'FGA', '3PM', '3PA',
    'FTM', 'FTA', 'OREB', 'DREB', 'REB', 'AST', 'STL','BLK',
    'TOV', 'PF', 'PLUS-MINUS'
]

boxscores = boxscores.reindex(columns=column_names)

# append and save files
timberwolves_games_2020_2021.to_csv("./data/ytd_timberwolves_games_pulled.csv", index=False)
boxscores.to_csv("./data/ytd_timberwolves_player_boxscore.csv", index=False)

# log to signal beginning of function execution
logging.info("ENDINGCALL_NBA_API JOB AT {}".format(datetime.datetime.now()))
