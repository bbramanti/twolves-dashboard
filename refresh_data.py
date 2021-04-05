import pandas as pd
import time
import logging
import datetime
from nba_api.stats.static import teams
from nba_api.stats.endpoints import boxscoretraditionalv2, teamgamelog
from dateutil.parser import parse
from retrying import retry

# configure logger
logging.basicConfig(level=logging.INFO)

# log to signal beginning of function execution
logging.info("BEGINNING REFRESH_DATA JOB AT {}".format(datetime.datetime.now()))

# read in current state of both csv files
# GAME_ID field may have leading zeroes, so read in as string
# if season field is not read in as string, will cause issues when dropping duplicates later in script
curr_games_pulled = pd.read_csv('./data/ytd_timberwolves_games_pulled.csv', dtype={'GAME_ID':str, 'SEASON':str})
logging.info("num records in games pulled: {}".format(len(curr_games_pulled)))
curr_player_boxscore = pd.read_csv('./data/ytd_timberwolves_player_boxscore.csv')
logging.info("num records in player boxscore: {}".format(len(curr_player_boxscore)))

# get Minnesota Timberwolves Team ID
teams_data = teams.get_teams()
minnesota_timberwolves_id = [team for team in teams_data if team['abbreviation'] == 'MIN'][0]['id']
logging.info("team id: {}".format(minnesota_timberwolves_id))

# calls nba api to get team's game log
# retry a maximum of 3 times, waiting 5 seconds between each retry
@retry(stop_max_attempt_number=3, wait_fixed=5000)
def get_team_game_log(team_id, year):
    logging.info("trying to get team's game log...")
    return teamgamelog.TeamGameLog(
        team_id=team_id,
        season=year
    ).get_data_frames()[0]

# get timberwolves game log
pull_year = "2020"
timberwolves_games_2020_2021 = get_team_game_log(team_id=minnesota_timberwolves_id, year=pull_year)

# add 'SEASON' column to separate seasons
timberwolves_games_2020_2021['SEASON'] = pull_year

# select only neccessary data
timberwolves_games_2020_2021 = timberwolves_games_2020_2021[['Game_ID', 'GAME_DATE', 'SEASON', 'MATCHUP', 'WL']]

# fix column names
timberwolves_games_2020_2021.rename(
    columns={
        'Game_ID': 'GAME_ID'
    },
    inplace=True
)

# change date column format from MAR 15, 2021 -> 3/15/2021
timberwolves_games_2020_2021['GAME_DATE'] = timberwolves_games_2020_2021.apply(lambda row : parse(row['GAME_DATE']).strftime('%m/%d/%Y'), axis = 1)

# sort by game date instead of game date because date would require parsing back to datetime object
timberwolves_games_2020_2021.sort_values(by=['GAME_ID'], inplace=True)

# remove all records from timberwolves_games_2020_2021 that exist in curr_games_pulled
timberwolves_games_2020_2021 = pd.concat([timberwolves_games_2020_2021,curr_games_pulled]).drop_duplicates(keep=False)
logging.info("pulling {} new games".format(len(timberwolves_games_2020_2021)))
print(timberwolves_games_2020_2021.sort_values(by=['GAME_ID']))

if not timberwolves_games_2020_2021.empty:

    # create Dataframe to hold BoxScore data
    boxscores = pd.DataFrame()

    # pull each game and append results to dataframe
    for index, game in timberwolves_games_2020_2021.iterrows():
        logging.info("pulling {} from {} with id {}".format(game['MATCHUP'], game['GAME_DATE'], game['GAME_ID']))
        game_instance = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=game['GAME_ID']).get_data_frames()[0]
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
    pd.concat([curr_games_pulled,timberwolves_games_2020_2021]).to_csv("./data/ytd_timberwolves_games_pulled.csv", index=False)
    pd.concat([curr_player_boxscore,boxscores]).to_csv("./data/ytd_timberwolves_player_boxscore.csv", index=False)

# log to signal end of function execution
logging.info("ENDING REFRESH_DATA JOB AT {}".format(datetime.datetime.now()))
