import pandas as pd
import numpy as np
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Output, Input
import plotly.express as px
import random
import logging

# read dataset into pandas dataframe from csv file
data = pd.read_csv("./data/ytd_timberwolves_player_boxscore.csv")
# convert DATE field into datetime field (necessary to work with line charts)
data["DATE"] = pd.to_datetime(data["DATE"], format="%m/%d/%Y")
# add % into data
data["FG-PCT"] = data["FGM"]/data["FGA"]
data["3-PCT"] = data["3PM"]/data["3PA"]

# initialize app
app = dash.Dash(__name__)
# server variable needed for procfile
server = app.server

# build layout (css contained in /assets)
app.layout = html.Div(
    id = "outer",
    children = [
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
                html.H1(className="chart-title", children=["PTS / AST / REB"]),
                dcc.Dropdown(
                    id = "player-filter",
                    options = [
                        {"label": player, "value": player}
                        for player in np.sort(data.PLAYER.unique())
                    ],
                    value = "Anthony Edwards",
                    clearable = False,
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
                        color_discrete_sequence=px.colors.qualitative.Light24,
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
                )
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

if __name__ == "__main__":
    logging.info("running application ...")
    app.run_server(debug=False)
