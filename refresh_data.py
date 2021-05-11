import datetime
import logging
import os
import pandas as pd
import sys
import time
from dateutil.parser import parse
from nba_api.stats.endpoints import boxscoretraditionalv2, teamgamelog
from nba_api.stats.static import teams

# configure logger
logging.basicConfig(level=logging.INFO)

# log to signal beginning of function execution
logging.info("BEGINNING REFRESH_DATA JOB AT {}".format(datetime.datetime.now()))

# team name must be sent in as argument "python refresh_data timberwolves"
team = sys.argv[1]
logging.info(team)

# check if any data exists for that team, if not create folder + data sources
if not os.path.isdir("./data/{}".format(team)):
    os.mkdir("./data/{}".format(team))
    with open('./data/{}/ytd_{}_games_pulled.csv'.format(team, team), 'w') as file_1:
        file_1.write('GAME_ID,GAME_DATE,SEASON,MATCHUP,WL\n')
    with open('./data/{}/ytd_{}_player_boxscore.csv'.format(team, team), 'w') as file_2:
        file_2.write('PLAYER,TEAM,DATE,MATCHUP,W/L,MIN,PTS,FGM,FGA,3PM,3PA,FTM,FTA,OREB,DREB,REB,AST,STL,BLK,TOV,PF,PLUS-MINUS\n')

# read in current state of both csv files
# GAME_ID field may have leading zeroes, so read in as string
# if season field is not read in as string, will cause issues when dropping duplicates later in script
curr_games_pulled = pd.read_csv('./data/{}/ytd_{}_games_pulled.csv'.format(team, team), dtype={'GAME_ID':str, 'SEASON':str})
logging.info("num records in games pulled: {}".format(len(curr_games_pulled)))
curr_player_boxscore = pd.read_csv('./data/{}/ytd_{}_player_boxscore.csv'.format(team, team))
logging.info("num records in player boxscore: {}".format(len(curr_player_boxscore)))

# get Team ID
teams_data = teams.get_teams()
team_id = [team_item for team_item in teams_data if team_item['nickname'].lower() == team.lower()][0]['id']
logging.info("team id: {}".format(team_id))

# calls nba api to get team's game log
def get_team_game_log(team_id, year):
    return teamgamelog.TeamGameLog(team_id=team_id,season=year).get_data_frames()[0]

# get game log
pull_year = "2020"
games_2020_2021 = get_team_game_log(team_id=team_id, year=pull_year)

# add 'SEASON' column to separate seasons
games_2020_2021['SEASON'] = pull_year

# select only neccessary data
games_2020_2021 = games_2020_2021[['Game_ID', 'GAME_DATE', 'SEASON', 'MATCHUP', 'WL']]

# fix column names
games_2020_2021.rename(
    columns={
        'Game_ID': 'GAME_ID'
    },
    inplace=True
)

# change date column format from MAR 15, 2021 -> 3/15/2021
games_2020_2021['GAME_DATE'] = games_2020_2021.apply(lambda row : parse(row['GAME_DATE']).strftime('%m/%d/%Y'), axis = 1)

# sort by game date
games_2020_2021.sort_values(by=['GAME_DATE'], inplace=True)

# remove all records from timberwolves_games_2020_2021 that exist in curr_games_pulled
games_2020_2021 = pd.concat([games_2020_2021,curr_games_pulled]).drop_duplicates(keep=False)
if games_2020_2021.empty:
    logging.info("pulling {} new games".format(len(games_2020_2021)))

if not games_2020_2021.empty:
    # pull no more than 5 games at a time
    games_2020_2021 = games_2020_2021[0:5]
    logging.info("pulling {} new games".format(len(games_2020_2021)))

    # create Dataframe to hold BoxScore data
    boxscores = pd.DataFrame()

    # pull each game and append results to dataframe
    for index, game in games_2020_2021.iterrows():
        logging.info("pulling {} from {} with id {}".format(game['MATCHUP'], game['GAME_DATE'], game['GAME_ID']))
        game_instance = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game['GAME_ID']).get_data_frames()[0]
        boxscores = boxscores.append(game_instance)
        time.sleep(5)

    # remove any records for the opposing team, or players who did not log any minutes
    boxscores = boxscores[
        (boxscores['TEAM_ID'] == team_id) &
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
    boxscores = boxscores.merge(games_2020_2021, on='GAME_ID', how='left')

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
    pd.concat([curr_games_pulled,games_2020_2021]).to_csv("./data/{}/ytd_{}_games_pulled.csv".format(team, team), index=False)
    pd.concat([curr_player_boxscore,boxscores]).to_csv("./data/{}/ytd_{}_player_boxscore.csv".format(team, team), index=False)

# log to signal end of function execution
logging.info("ENDING REFRESH_DATA JOB AT {}".format(datetime.datetime.now()))
