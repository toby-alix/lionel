import plotly.graph_objects as go
import plotly.express as px

from app.src.get_data.connector import PostgresConnector
from app.src.get_data.scrape_fpl import FPLScraper

""" 
TODO: 
    Declare player data frames at the top of script and pass that to each func, rather than repeatedly pulling from DB (slow af)
    Vis to add: hidden gems? Low ownership players (points, cost, size = ownership)
    Variance of players
    Top players by position
    Something about win odds

"""


class Chart:

    def __init__(self, connector):
        self.con = connector


class TeamChoiceChart(Chart):
    
    def __init__(self, connector, line_width=3):
        super().__init__(connector)
        self.line_width = line_width


    def _create_pitch(self): 
        line_width = self.line_width

        fig = go.Figure()

        fig.add_vrect(
            x0=-350, x1=350, # width=3
            line=dict(
                color='#4B5563',
                width=4
            )
        )

        fig.add_trace(go.Scatter(
            x=[-350, 350],
            y=[0, 0],
            marker=dict(size=25, color='#4B5563'),
            mode='lines',
            line=dict(
                color='#4B5563',
                width=line_width
            )
        ))

        fig.add_shape(type="circle",
            xref="x", yref="y",
            x0=-100, y0=-100, x1=100, y1=100,
            line=dict(
                color='#4B5563',
                width=line_width-1
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[-180, -180, 180, 180],
                y=[-550, -400,  -400, -550, ],
                mode='lines',
                line_color="#4B5563",
                showlegend=False,
                line=dict(
                    color='#4B5563',
                    width=line_width
                )
            )
        )

        fig.add_trace(
            go.Scatter(
                x=[-180, -180, 180, 180],
                y=[550, 400,  400, 550, ],
                mode='lines',
                line_color="#4B5563",
                showlegend=False,
                line=dict(
                    color='#4B5563',
                    width=line_width
                )
            )
        )
        
        fig.update_layout(
            font_family="sans-serif",
            autosize=False,
            width=600,
            height=800,
            yaxis_range=[-550,550],
            xaxis_range=[-400,400],
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        fig.update_xaxes(visible=False)  
        fig.update_yaxes(visible=False)

        return fig


    def _plot_players(self, first_xi, position, fig):
        df = first_xi.loc[first_xi.position == position]

        Y = {
            'FWD': 350,
            'MID': 75,
            'DEF': -250,
            'GK': -475
        }

        dims = [-250, 250]
        width = dims[1] - dims[0]
        
        if len(df) > 1:
            divisor = len(df) - 1
            jump = int(width/divisor)
            X = list(range(dims[0], dims[1]+1, jump) )
        else:
            X = [0]
        
        fig.add_trace(
            go.Scatter(
                x=X,
                y=[Y[position]]*len(df),
                mode='markers+text',
                marker=dict(
                    size=25,
                    color='#4B5563'
                ),  
                
                text=df['surname'],
                textposition='bottom center',
                textfont=dict(color='#4B5563'),
                textfont_size=10,
                
                customdata=df[['agg_win_odds', 'team_name', 'total_points', 'next_opp', 'name', 'value']],
            
                hovertemplate=
                    '<b>%{customdata[4]}</b>' + 
                    '<br><br><b>Total points:</b> %{customdata[2]}' + 
                    '<br><b>Price:</b> %{customdata[5]}' +
                    '<br><b>Team:</b> %{customdata[1]}' + 
                    '<br><b>Next opponent:</b> %{customdata[3]}' + 
                    '<br><b>Odds of a win in next GW:</b> %{customdata[0]:.0%}'  +  '<extra></extra>'
            )
        )
        
        return fig


    def _plot_subs(self, team, fig):
        
        df = team.loc[team.first_xi == 0]
        
        X = [375]*4
        Y = [-90, -30, 30, 90 ]
            
        fig.add_trace(
            go.Scatter(
                x=X,
                y=Y,
                mode='markers',
                marker=dict(
                    size=25,
                    color='#4B5563'
                ),  
                
                text=df['name'],
                textposition='bottom left',
                textfont=dict(color='#4B5563'),
                textfont_size=10,
                
                customdata=df[['agg_win_odds', 'team_name', 'total_points', 'next_opp', 'name', 'value']],
                
                hovertemplate=
                    '<b>%{text}</b>' + 
                    '<br><br><b>Total points:</b> %{customdata[2]}' + 
                    '<br><b>Price:</b> %{customdata[5]}' +
                    '<br><b>Team:</b> %{customdata[1]}' + 
                    '<br><b>Next opponent:</b> %{customdata[3]}' + 
                    '<br><b>Odds of a win in next GW:</b> %{customdata[0]:.0%}'  +  '<extra></extra>'
            )
        )
        return fig


    def create_plot(self, gameweek, season=23):
        
        con = self.con
        try:
            players = con.get_team(gameweek, season)
        except Exception:
            players = con.get_team(gameweek-1, season)

        team = players[players['picked'] == 1]
        first_xi = team.loc[team['first_xi'] == 1]

        fig = self._create_pitch()
        for pos in ['FWD', 'MID', 'DEF', 'GK']:
            self._plot_players(first_xi, pos, fig)

        fig = self._plot_subs(team, fig)

        return fig
    

class PlayerValueChart(Chart):

    def __init__(self, connector: PostgresConnector, min_games=2, season=23):
        super().__init__(connector)
        self.min_games = min_games
        self.season = season


    def plot_value(self, gameweek, season=23):

        con = self.con
        try:
            collapsed_stats = con.get_team(gameweek, season)
        except Exception:
            collapsed_stats = con.get_team(gameweek-1, season)
        
        collapsed_stats['Season Value'] = collapsed_stats.total_points / collapsed_stats.value
        collapsed_stats = collapsed_stats[collapsed_stats['minutes']/90 > self.min_games] 

        team_players = collapsed_stats[collapsed_stats['picked'] == 1]
        non_team_players = collapsed_stats[collapsed_stats['picked'] != 1]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=non_team_players.value,
            y=non_team_players['Season Value'],
            marker=dict(
                color='#9fbbe3', 
            ),
            mode='markers',
            
            customdata=non_team_players[['agg_win_odds', 'team_name', 'total_points', 'next_opp', 'name', 'value']],

            hovertemplate=
                '<b>%{customdata[4]}</b>' + 
                '<br><br><b>Total points:</b> %{customdata[2]}' + 
                '<br><b>Price:</b> %{customdata[5]}' +
                '<br><b>Team:</b> %{customdata[1]}'  +  '<extra></extra>'
            
        ))

        fig.add_trace(go.Scatter(
            x=team_players.value,
            y=team_players['Season Value'],
            marker=dict(
                color='#4B5563', 
            ),
            mode='markers',
            customdata=team_players[['agg_win_odds', 'team_name', 'total_points', 'next_opp', 'name', 'value']],

            hovertemplate=
                '<b>%{customdata[4]}</b>' + 
                '<br><br><b>Total points:</b> %{customdata[2]}' + 
                '<br><b>Price:</b> %{customdata[5]}' +
                '<br><b>Team:</b> %{customdata[1]}' +  '<extra></extra>'
        ))

        fig.update_layout(
            autosize=False,
            width=700,
            height=800,
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Player cost",
            yaxis_title="Cost/Points",
            yaxis_visible=True, 
            yaxis_showticklabels=False,
            xaxis_visible=True, 
            xaxis_showticklabels=False,
            font=dict(
                family="sans-serif",
                color="#4B5563"
            )
        )

        fig.add_annotation(text="Minimum 2 games. Dark points show players picked for the upcoming gameweek.",
                        xref="paper", yref="paper",
                        x=0, y=-0.1, showarrow=False)

        return fig


# class SleptOnChart(Chart):
#     def __init__(self):
#         super().__init__()
#         self.scraper = FPLScraper(season=23)
#         self.selected = self.scraper.df_gw_stats
    

#     def plot_slept_on(self, gameweek, season=23):
#         selected = self.selected
#         selected = selected[selected['season'] == 23]
#         selected = selected.drop_duplicates().reset_index()

#         con = self.con
#         slept_on = con.get_team(gameweek, season)
#         slept_on = slept_on[slept_on['minutes'] > slept_on[slept_on['minutes'] > 0]['minutes'].quantile(0.25)]

#         slept_on = slept_on.merge(selected[['name', 'selected']], how='left', left_on='name', right_on='name')
#         slept_on = slept_on.sort_values(by=['selected'])
#         slept_on.loc[slept_on['scaled_points'] < 0] = 0
#         slept_on.loc[slept_on['picked'] == 1, 'picked'] = 'yes'
#         slept_on.loc[slept_on['picked'] == 0, 'picked'] = 'no'
#         slept_on = slept_on.rename(columns={'total_points':'Season points'})

#         fig = px.scatter(data_frame=slept_on, x='selected', y='scaled_points', 
#                     size='Season points', 
#                     color='picked', 
#                     color_discrete_sequence=[ '#9fbbe3', '#4B5563',],
#                     hover_name="name",
#                     hover_data={
#                         'picked':False,
#                         'scaled_points':False,
#                         'selected':False,
#                     }
#              )

#         fig.update_layout(
#                 autosize=False,
#                 width=700,
#                 height=800,
#                 showlegend=False,
#                 paper_bgcolor='rgba(0,0,0,0)',
#                 plot_bgcolor='rgba(0,0,0,0)',
#                 xaxis_title="Selected by (players)",
#                 yaxis_title="Season points",
#                 yaxis_showticklabels=False,
#                 xaxis_visible=True, 
#                 xaxis_showticklabels=False,
#                 font=dict(
#                     family="sans-serif",
#                     color="#4B5563"
#                 )
#             )

#         fig.add_shape(type="rect",
#             x0=0, y0=0.4, x1=1700000, y1=0.9,
#             line_color="#4B5563",
#             line_width=2, opacity=0.5, line_dash="dot",
#         )

#         fig.add_annotation(text="Marker size indicates expected points in the next GW. Dark points show players picked for the upcoming gameweek.",
#                             xref="paper", yref="paper",
#                             x=0, y=-0.1, showarrow=False)

#         fig.add_annotation( # add a text callout with arrow
#             text="Differential zone", x=880000, y=0.92, arrowhead=1, showarrow=False
#         )

#         return fig

    

# def plot_slept_on():
#     selected = pd.read_sql('''
#         SELECT name, LAST_VALUE(selected) OVER(PARTITION BY name ORDER BY "GW" RANGE BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) selected FROM "GWStats" 
#     ''', db.engine)  # Not a great sql query but eh

#     selected = selected.drop_duplicates().reset_index()

#     slept_on = get_latest_team(db)
#     slept_on = slept_on[slept_on['minutes'] > slept_on[slept_on['minutes'] > 0]['minutes'].quantile(0.25)]
#     slept_on = slept_on.merge(selected[['name', 'selected']], how='left', left_on='name', right_on='name')
#     slept_on = slept_on.sort_values(by=['selected'])
#     slept_on.loc[slept_on['scaled_points'] < 0] = 0
#     slept_on.loc[slept_on['picked'] == 1, 'picked'] = 'yes'
#     slept_on.loc[slept_on['picked'] == 0, 'picked'] = 'no'
#     slept_on = slept_on.rename(columns={'total_points':'Season points'})

#     fig = px.scatter(data_frame=slept_on, x='selected', y='scaled_points', 
#                     size='Season points', 
#                     color='picked', 
#                     color_discrete_sequence=[ '#9fbbe3', '#4B5563',],
#                     hover_name="name",
#                     hover_data={
#                         'picked':False,
#                         'scaled_points':False,
#                         'selected':False,
#                     }
#     )


#     fig.update_layout(
#             autosize=False,
#             width=700,
#             height=800,
#             showlegend=False,
#             paper_bgcolor='rgba(0,0,0,0)',
#             plot_bgcolor='rgba(0,0,0,0)',
#             xaxis_title="Selected by (players)",
#             yaxis_title="Season points",
#     #         yaxis_visible=False, 
#             yaxis_showticklabels=False,
#             xaxis_visible=True, 
#             xaxis_showticklabels=False,
#             font=dict(
#                 family="sans-serif",
#                 color="#4B5563"
#             )
#         )

#     fig.add_shape(type="rect",
#         x0=0, y0=0.4, x1=1700000, y1=0.9,
#         line_color="#4B5563",
#         line_width=2, opacity=0.5, line_dash="dot",
#     )

#     fig.add_annotation(text="Marker size indicates expected points in the next GW. Dark points show players picked for the upcoming gameweek.",
#                         xref="paper", yref="paper",
#                         x=0, y=-0.1, showarrow=False)

#     fig.add_annotation( # add a text callout with arrow
#         text="Differential zone", x=880000, y=0.92, arrowhead=1, showarrow=False
#     )

#     return fig


# def plot_variance():
#     players = get_latest_team(db)[:50]
#     players = players.sort_values(by=['total_points'], ascending=False).reset_index()
#     picked_colors = ['#4B5563' if player in list(players[players['picked'] == 1].name.unique()) else '#9fbbe3' for player in players.name]

    
#     fig = px.strip(data_frame=players,
#                 x='name', 
#                 y='total_points', 
#                 color_discrete_sequence=picked_colors,
#                 color='name',
#                 labels={
#                         "total_points": "Points in gameweek",
#                         "name": ""
#                     },
#             )
#     fig.update_xaxes(tickangle=90)
#     fig.update_layout(
#             autosize=False,
#             width=1500,
#             height=800,
#             showlegend=False,
#             paper_bgcolor='rgba(0,0,0,0)',
#             plot_bgcolor='rgba(0,0,0,0)',
#     #         xaxis_title="Player cost",
#     #         yaxis_title="Cost/Points",
#             yaxis_visible=True, 
#             yaxis_showticklabels=False,
#             xaxis_visible=True, 
#     #         xaxis_showticklabels=False,
#             font=dict(
#                 family="sans-serif",
#                 color="#4B5563"
#             )
#         )

#     fig.add_annotation(text="Highest scoring players on the left. Dark points show players picked for the upcoming gameweek.",
#                         xref="paper", yref="paper",
#                         x=0, y=-0.5, showarrow=False)

#     fig.show()

#     return fig