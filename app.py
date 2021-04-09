import pandas as pd
import numpy as np
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
import plotly.express as px
import random
import logging

# read dataset into pandas dataframe from csv file
data = pd.read_csv("./data/timberwolves/ytd_timberwolves_player_boxscore.csv")
# convert DATE field into datetime field (necessary to work with line charts)
data["DATE"] = pd.to_datetime(data["DATE"], format="%m/%d/%Y")
# add % into data
data["FG-PCT"] = round(data["FGM"]/data["FGA"] * 100, 1)
data["3-PCT"] = round(data["3PM"]/data["3PA"] * 100, 1)
# position new columns
data.insert(9, 'FG-PCT', data.pop('FG-PCT'))
data.insert(12, '3-PCT', data.pop('3-PCT'))

# create game list, used in dropdown menu
game_list = data[["DATE", "MATCHUP"]].drop_duplicates(['DATE','MATCHUP'], keep='last')

# create team record
games_pulled = pd.read_csv("./data/timberwolves/ytd_timberwolves_games_pulled.csv", dtype={'SEASON':str})
wins = len(games_pulled[(games_pulled['SEASON'] == '2020') & (games_pulled['WL'] == 'W')])
losses = len(games_pulled[(games_pulled['SEASON'] == '2020') & (games_pulled['WL'] == 'L')])

# initialize app
app = dash.Dash(__name__)
app.title = "NBA Stats"
# server variable needed for procfile
server = app.server

# build layout (css contained in /assets)
app.layout = html.Div(
    id = "outer",
    children = [
        html.Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        html.Div(
            id = "inner-1",
            children = [
                html.Img(
                    id = "logo",
                    src = "https://cdn.freebiesupply.com/images/large/2x/minnesota-timberwolves-logo-transparent.png"
                )
            ]
        ),
        html.Div(
            id = "inner-2",
            children = [
                html.H1(className="chart-title", children=["BOX SCORES"]),
                dcc.Dropdown(
                    id = "game-filter",
                    options = [
                        {"label": matchup + " (" + date.strftime("%b %d, %Y") + ")", "value": date.strftime("%m/%d/%Y") + "," + matchup}
                        for date, matchup in game_list.values
                    ],
                    value = "12/23/2020,MIN vs. DET",
                    clearable = False,
                    searchable=False,
                    className = "dropdown"
                ),
                dash_table.DataTable(
                    id='game-table',
                    columns=[{"name": i, "id": i} for i in data.columns],
                    style_header={
                        'backgroundColor': 'rgb(17, 17, 17)'
                    },
                    style_cell={
                        'backgroundColor': 'rgb(17, 17, 17)',
                        'color': 'white',
                        'textAlign': 'left'
                    },
                    style_data_conditional=[
                        {
                            "if": {"state": "selected"},
                            "backgroundColor": "rgb(17, 17, 17)",
                            "border": "1px solid #78be20",
                        }
                    ],
                    style_table={'overflowX': 'auto'},
                    sort_action="native",
                    sort_mode="multi"
                ),
                html.H1(className="chart-title", children=["PTS / AST / REB"]),
                dcc.Dropdown(
                    id = "player-filter",
                    options = [
                        {"label": player, "value": player}
                        for player in np.sort(data.PLAYER.unique())
                    ],
                    value = "Anthony Edwards",
                    clearable = False,
                    searchable=False,
                    className = "dropdown"
                ),
                dcc.Graph(id="points-chart"),
                dcc.Graph(id="assists-chart"),
                dcc.Graph(id="rebounds-chart"),
                html.H1(className="chart-title", children=["MINUTES & +/-"]),
                dcc.Graph(
                    id="team-min-chart",
                    figure = px.line(
                        data,
                        x="DATE",
                        y="MIN",
                        color="PLAYER",
                        color_discrete_sequence=px.colors.qualitative.Light24,
                        title='Minutes (YTD)',
                        custom_data = ["MATCHUP", "W/L", "PLAYER"],
                        template = 'plotly_dark'
                    ).for_each_trace(
                        # any player averaging less than 25 minutes a game, do not show their trace (line)
                        lambda trace: trace.update(
                            visible='legendonly',
                            hovertemplate = '<b>%{customdata[2]}</b>' +
                                            '<br><b>Matchup</b>: %{customdata[0]}<br>' +
                                            '<b>Date</b>: %{x}<br>'+
                                            '<b>Win/Loss</b>: %{customdata[1]}<br>' +
                                            '<b>Minutes</b>: %{y}<br>' + '<extra></extra>',
                            mode='markers+lines') if np.mean(trace.y) < 25 else (trace.update(
                                visible=True,
                                mode='markers+lines',
                                hovertemplate = '<b>%{customdata[2]}</b>' +
                                                '<br><b>Matchup</b>: %{customdata[0]}<br>' +
                                                '<b>Date</b>: %{x}<br>'+
                                                '<b>Win/Loss</b>: %{customdata[1]}<br>' +
                                                '<b>Minutes</b>: %{y}<br>' + '<extra></extra>',
                            )
                            )
                    )
                ),
                dcc.Graph(
                    id="team-plus-minus-chart",
                    figure = px.bar(
                        data,
                        x="DATE",
                        y="MIN",
                        color="PLUS-MINUS",
                        color_continuous_scale=["red", "green"],
                        title='Minutes vs. +/- (YTD)',
                        custom_data = ["MATCHUP", "W/L", "PLAYER", "PLUS-MINUS"],
                        template = 'plotly_dark'
                    ).for_each_trace(
                        # any player averaging less than 0 +/- a game, do not show their trace (line)
                        lambda trace: trace.update(
                            visible='legendonly',
                            hovertemplate = '<b>%{customdata[2]}</b>' +
                                            '<br><b>Matchup</b>: %{customdata[0]}<br>' +
                                            '<b>Date</b>: %{x}<br>'+
                                            '<b>Win/Loss</b>: %{customdata[1]}<br>' +
                                            '<b>Minutes</b>: %{y}<br>' +
                                            '<b>+/-</b>: %{customdata[3]}<br>' + '<extra></extra>',
                            ) if np.mean(trace.y) < -3 else (trace.update(
                                visible=True,
                                hovertemplate = '<b>%{customdata[2]}</b>' +
                                                '<br><b>Matchup</b>: %{customdata[0]}<br>' +
                                                '<b>Date</b>: %{x}<br>'+
                                                '<b>Win/Loss</b>: %{customdata[1]}<br>' +
                                                '<b>Minutes</b>: %{y}<br>' +
                                                '<b>+/-</b>: %{customdata[3]}<br>' + '<extra></extra>',
                            )
                            )
                    )
                ),
                html.H1(className="chart-title", children=["Season Totals"]),
                dcc.Dropdown(
                    id = "season-totals-filter",
                    options = [
                        {
                            "label": "Points", "value": "PTS"
                        },
                        {
                            "label": "Rebounds", "value": "REB"
                        },
                        {
                            "label": "Assists", "value": "AST"
                        }
                    ],
                    value = "PTS",
                    clearable = False,
                    searchable=False,
                    className = "dropdown"
                ),
                dcc.Graph(id="season-totals-chart"),
                html.H1(className="record-title", children=["Record: ({} - {})".format(wins, losses)])
            ]
        )
    ]
)

@app.callback(
    [Output("points-chart", "figure"), Output("assists-chart", "figure"), Output("rebounds-chart", "figure")],
    Input("player-filter", "value")
)
def update_charts(player):
    filtered_data = data[data["PLAYER"] == player]
    pts_fig = px.line(
        filtered_data,
        x="DATE",
        y="PTS",
        title='Points (YTD)',
        custom_data = ["MATCHUP", "W/L"],
        template = 'plotly_dark'
    )
    pts_fig.update_traces(
        mode='markers+lines',
        line_color="#78be20",
        hovertemplate = '<b>' + player + '</b>' +
                        '<br><b>Matchup</b>: %{customdata[0]}<br>' +
                        '<b>Date</b>: %{x}<br>'+
                        '<b>Win/Loss</b>: %{customdata[1]}<br>' +
                        '<b>Points</b>: %{y}<br>' + '<extra></extra>'
    )
    ast_fig = px.line(
        filtered_data,
        x="DATE",
        y="AST",
        title='Assists (YTD)',
        custom_data = ["MATCHUP", "W/L"],
        template = 'plotly_dark'
    )
    ast_fig.update_traces(
        mode='markers+lines',
        line_color="#78be20",
        hovertemplate = '<b>' + player + '</b>' +
                        '<br><b>Matchup</b>: %{customdata[0]}<br>' +
                        '<b>Date</b>: %{x}<br>'+
                        '<b>Win/Loss</b>: %{customdata[1]}<br>' +
                        '<b>Assists</b>: %{y}<br>' + '<extra></extra>'
    )
    reb_fig = px.line(
        filtered_data,
        x="DATE",
        y="REB",
        title='Rebounds (YTD)',
        custom_data = ["MATCHUP", "W/L"],
        template = 'plotly_dark'
    )
    reb_fig.update_traces(
        mode='markers+lines',
        line_color="#78be20",
        hovertemplate = '<b>' + player + '</b>' +
                        '<br><b>Matchup</b>: %{customdata[0]}<br>' +
                        '<b>Date</b>: %{x}<br>'+
                        '<b>Win/Loss</b>: %{customdata[1]}<br>' +
                        '<b>Rebounds</b>: %{y}<br>' + '<extra></extra>'
    )
    return pts_fig, ast_fig, reb_fig

@app.callback(
    [Output("game-table", "data"), Output("game-table", "style_data_conditional")],
    Input("game-filter", "value")
)
def update_table(game):
    date,matchup = game.split(",")
    filtered_data = data[(data["MATCHUP"] == matchup) & (data["DATE"] == date)].sort_values(by=['PLAYER'])
    # change date so in web view it doesn't display like 2020-12-23T00:00:00 instead 12/23/2020
    filtered_data["DATE"] = filtered_data["DATE"].dt.strftime("%m/%d/%Y")
    style_data_conditional=[
        {
            "if": {"state": "selected"},
            "backgroundColor": "inherit !important",
            "border": "inherit !important",
        },

        {
            'if': {
                'filter_query': '{{PLUS-MINUS}} = {}'.format(filtered_data['PLUS-MINUS'].max()),
                'column_id': 'PLUS-MINUS'
            },
            "color": "green",
        },

        {
            'if': {
                'filter_query': '{{PLUS-MINUS}} = {}'.format(filtered_data['PLUS-MINUS'].min()),
                'column_id': 'PLUS-MINUS'
            },
            "color": "red",
        },
    ]
    return filtered_data.to_dict('records'), style_data_conditional

@app.callback(
    Output("season-totals-chart", "figure"),
    Input("season-totals-filter", "value")
)
def generate_chart(value):
    fig = px.pie(data, names="PLAYER", values=value, template='plotly_dark', color_discrete_sequence=px.colors.qualitative.Light24)
    hover_values = {
        "PTS": "Points",
        "REB": "Rebounds",
        "AST": "Assists",
    }
    fig.update_traces(
        hovertemplate = '<b>' + "%{label}" + '</b>'
                        '<br><b>' + hover_values[value] + '</b>: %{value}'

    )
    return fig

if __name__ == "__main__":
    app.run_server(debug=False)
