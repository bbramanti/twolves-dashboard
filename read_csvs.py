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
logging.info("BEGINNING READ CSVS JOB AT {}".format(datetime.datetime.now()))

# read in current state of both csv files
# GAME_ID field may have leading zeroes, so read in as string
curr_games_pulled = pd.read_csv('./data/ytd_timberwolves_games_pulled.csv', dtype={'GAME_ID':str})
logging.info("num records in games pulled: ".format(len(curr_games_pulled)))
curr_player_boxscore = pd.read_csv('./data/ytd_timberwolves_player_boxscore.csv')
logging.info("num records in player boxscore: ".format(len(curr_games_pulled)))

# log to signal beginning of function execution
logging.info("BEGINNING READ CSVS JOB AT {}".format(datetime.datetime.now()))
