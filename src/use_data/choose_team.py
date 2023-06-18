import numpy as np
import datetime as dt
from pulp import LpVariable, LpProblem, lpSum, LpMaximize

from app.src.get_data.connector_sql import PostgresConnector

class Team:

    def __init__(self, season, gameweek, scraper_fpl, odds_weight_def=0.6, odds_weight_fwd=0.4):
        self.season = season
        self.gameweek = gameweek
        self.odds_weight_def = odds_weight_def
        self.odds_weight_fwd = odds_weight_fwd
        self.scraper_fpl = scraper_fpl


    def _shape_fixtures_for_player_merge(self):
        
        fixtures = self.scraper_fpl.get_season_fixtures()

        fixtures_1 = fixtures[['home', 'away', 'game_date', 'gameweek']]
        fixtures_2 = fixtures[['home', 'away', 'game_date', 'gameweek']]
        fixtures_1['is_home'] = True
        fixtures_2['is_home'] = False
        fixtures_1 = fixtures_1.rename({'home': 'team_name', 'away': 'next_opponent_name'}, axis=1)
        fixtures_2 = fixtures_2.rename({'away': 'team_name', 'home': 'next_opponent_name'}, axis=1)
        
        fixtures = fixtures_1.append(fixtures_2)
        
        return fixtures


    def _collapse_past_games(self, current_gw, games_window=30):
        """Collapse gameweek by gameweek stats until the latest gw"""

        next_gw = current_gw + 1
        season = int(self.season)

        df = self.scraper_fpl.get_gw_stats()
        df['season'] = df['season'].astype(int)
        
        df = df.reset_index(drop=True)
        if current_gw < 5: 
            df = df[(
                    (df['GW'] < current_gw) & (df['GW'] > current_gw - games_window) & (df['season'] == season)
            ) | (
                    (df['GW'] > current_gw + 38 - games_window) & (df['season'] == season - 1)
            )]
        else:
            df = df[(df['season'] == season)]

        df = df.groupby(['name']).agg({
            'total_points': 'sum',
            'team_name': 'last',
            'value': 'last',
            'ict_index': 'mean',
            'minutes': 'sum',
            'position': 'last',
            'team_id': 'last',
        })

        df['season'] = season
        df = df.reset_index()
        df['next_gw'] = next_gw
        return df 


    @staticmethod
    def _sum_player_stats(current_gw, _df_shaped_fixtures, df_collapsed_players):
            
        df_fixtures = _df_shaped_fixtures[_df_shaped_fixtures['gameweek'] == current_gw+1]

        df_collapsed_players = df_collapsed_players.rename(columns={'team_name': 'team' })
        df_collapsed_players = df_collapsed_players.merge(df_fixtures, left_on='team', right_on='team_name', how='left')
        df_collapsed_players = df_collapsed_players.drop('team_name', axis=1)
        
        df_collapsed_players = df_collapsed_players.dropna()
        df_collapsed_players = df_collapsed_players.rename(columns={'team':'team_name'})
        
        return df_collapsed_players

    # 1) To be moved into a class that combines odds and fpl
    @staticmethod
    def _shape_home_away_fixtures(df_players, df_odds):
        next_home_df = df_players[df_players['is_home']]
        next_away_df = df_players[df_players['is_home'] == False]

        df_odds[['home', 'away']] = df_odds[['home', 'away']].apply(lambda x: x.str.strip(), axis=0)    
        
        if df_odds['season'].dtype != 'int64':
            df_odds['season'] = df_odds['season'].str.slice(start=-2).astype(int)
    
        next_home_df = next_home_df.merge(df_odds, left_on=['team_name', 'season', 'next_opponent_name'], right_on=['home', 'season', 'away'], how='left')
        next_away_df = next_away_df.merge(df_odds, left_on=['team_name', 'season', 'next_opponent_name'], right_on=['away', 'season', 'home'], how='left')
        df_next_game = next_home_df.append(next_away_df)
        return df_next_game

    # 2) To be moved into a class that combines odds and fpl
    @staticmethod
    def _shape_double_gameweeks(df_next_game):

        COLS = ['name', 'team_name', 'total_points', 'value', 'ict_index', 'minutes', 'position', 'is_home', 'home_odds', 'draw_odds', 'away_odds', 'home', 'away']
        pivot = df_next_game[COLS]

        # Account for gameweeks with two games
        g = pivot.groupby(['name', 'team_name', 'total_points', 'value', 'ict_index', 'minutes', 'position',]).cumcount().add(1)
        pivot = pivot.set_index(['name', 'team_name', 'total_points', 'value', 'ict_index', 'minutes', 'position', g]).unstack().sort_index(axis=1, level=1)
        pivot.columns = ["{}{}".format(a, b) for a, b in pivot.columns]
        pivot = pivot.reset_index()
        pivot['win_odds1'] = np.where(pivot['home1'] == pivot['team_name'], pivot['home_odds1'], pivot['away_odds1'])
        
        # Aggregate win odds where there are twp games
        if 'home2' in pivot.columns:
            pivot['win_odds2'] = np.where(pivot['home2'] == pivot['team_name'], pivot['home_odds2'], pivot['away_odds2'])
            
            # Arbitrarily add 20% because the players still get more game time for points even if they are unlikely to win either.
            pivot['agg_win_odds'] =  np.where(~pivot['home2'].isna(), ((pivot['win_odds1'] + pivot['win_odds2']) - (pivot['win_odds1'] * pivot['win_odds2'])), pivot['win_odds1'])
        
        else:
            pivot['agg_win_odds'] = pivot['win_odds1']

        return pivot


    def _prepare_data(self, connector):

        # Odds
        con = connector
        df_odds = con.get_win_odds(self.season, self.gameweek+1)
        
        # FPL data
        df_fixtures = self._shape_fixtures_for_player_merge()
        df_collapsed_players = self._collapse_past_games(self.gameweek)
        df_players = self._sum_player_stats(self.gameweek, df_fixtures, df_collapsed_players)

        # Combine FPL and betting data
        df_next_game = self._shape_home_away_fixtures(df_players, df_odds)
        df_next_game = self._shape_double_gameweeks(df_next_game)

        # Cleaning
        df_next_game['games_played'] = df_next_game['minutes'] / 90
        df_next_game['scaled_points'] = df_next_game['total_points'] / df_next_game['total_points'].max()
        df_next_game['next_gw'] = self.gameweek+1
    
        df_next_game['points_weighted'] = np.where(df_next_game.position.isin(['DEF', 'GK']), 
                                        ((1-self.odds_weight_def) * df_next_game['scaled_points']) + (self.odds_weight_def * df_next_game['agg_win_odds']), 
                                        ((1-self.odds_weight_fwd) * df_next_game['scaled_points']) + (self.odds_weight_fwd * df_next_game['agg_win_odds'])
                                        )  

        df_next_game['next_opp'] = np.where(df_next_game.team_name == df_next_game.away1, df_next_game.home1, df_next_game.away1)
        df_next_game['surname'] = df_next_game.name.apply(lambda x: x.split()[-1])
        
        return df_next_game


    @staticmethod
    def _pick_xv(player_df, maximisation_var="value_fixture", BUDGET=1000, testing=False):
        """
        Picks a team of 15 players

        Parameters:
            player_df (df): dataframe of player stats

        returns:
            team (df): 15 players
        """

        pos_available = {
            'DEF': 5,
            'FWD': 3,
            'MID': 5,
            'GK': 2,
        }

        player_df = player_df.fillna(0).reset_index()

        teams = player_df.team_name.to_list()
        positions = player_df.position.to_list()
        total_points = player_df.total_points.to_list() 
        points_weighted = player_df.points_weighted.to_list() 
        
        players = [LpVariable("player_" + str(i), cat="Binary") for i in player_df.index] 
        captain_decisions = [LpVariable("captain_" + str(i), cat="Binary") for i in player_df.index]

        prob = LpProblem("FPL Player Choices", LpMaximize)
        
        # Objective - I want to maximise next fixture with total points - how do I combine them? Scale them both and then take the mean of the two?
        if maximisation_var == "value_fixture":
            prob += lpSum((players[i] + captain_decisions[i]) * points_weighted[i]  for i in range(len(player_df))) 
        else: 
            prob += lpSum((players[i] + captain_decisions[i]) * total_points[i]  for i in range(len(player_df))) 
        
        # Constraints
        prob += sum(players) ==  15
        prob += lpSum(players[i] * player_df.value[player_df.index[i]] for i in range(len(player_df))) <= BUDGET
        prob += sum(captain_decisions) == 1
        
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            prob += lpSum(players[i] for i in range(len(player_df)) if positions[i] == pos) <= pos_available[pos]

        for club in teams:
            prob += lpSum(players[i] for i in range(len(player_df)) if teams[i] == club) <= 3 # Club Limit
        
        for i in range(len(player_df)):
            prob += (players[i] - captain_decisions[i]) >= 0
            
        # LpSolverDefault.msg = 1
        prob.solve()
        
        players = [player for player in players if player.varValue != 0]
        captain = [player for player in captain_decisions if player.varValue != 0]
        captain_index = int(captain[0].name.split("_")[1])
        
        indices = [int(player.name.split("_")[1]) for player in players]

        team_2 = player_df.copy(deep=True)
        team_2.loc[indices, 'picked'] = 1
        team_2.loc[team_2['picked'] != 1, 'picked'] = 0
        team_2['captain'] = 0
        team_2.loc[captain_index, 'captain'] = 1

        team_2 = team_2.drop('index', axis=1).reset_index()
        return team_2
    

    def pick_xi(self, connector):
        
        player_df = self._prepare_data(connector)
        team = self._pick_xv(player_df)
        
        other_players = team.loc[team['picked'] != 1]
        team = team.loc[team['picked'] == 1]
        
        positions = team.position.to_list()
        points_weighted = team.points_weighted.to_list() 
        
        pos_limits = {
            'DEF': [3, 5],
            'FWD': [1, 3],
            'MID': [2, 5],
            'GK': [1, 1],
        }
        
        players = [LpVariable("player_" + str(i), cat="Binary") for i in team.index]
        
        prob = LpProblem("First team choices", LpMaximize)
        
        prob += lpSum(players[i] * points_weighted[i] for i in range(len(team))) 
        prob += sum(players) ==  11
        
        for pos in ['GK', 'DEF', 'MID', 'FWD']:
            prob += lpSum(players[i] for i in range(len(team)) if positions[i] == pos) >= pos_limits[pos][0]
            prob += lpSum(players[i] for i in range(len(team)) if positions[i] == pos) <= pos_limits[pos][1]
        
        prob.solve()
            
        players = [player for player in players if player.varValue != 0]
        indices = [int(player.name.split("_")[1]) for player in players]
        
        team['first_xi'] = 0
        team.loc[indices, 'first_xi'] = 1
        team = team.sort_values('first_xi', ascending=False)
        team = team.drop('index', axis=1).reset_index(drop=True)
        
        team = team.append(other_players)
        team['season'] = self.season
        team['picked_time'] = dt.datetime.now() 

        for col in ['is_home1', 'is_home2', 'is_home3']:
            if col in team.columns:
                team[col] = team[col].replace({0: np.nan, float(0): np.nan})

        self.first_xi = team


class TeamPointsChecker:
    def __init__(self, connector: PostgresConnector):
        self.connector = connector

    
    def check_points(self, gameweek, season):
        team = self.connector.get_team(gameweek, season)
        team = team[team.first_xi == 1]
        pass



