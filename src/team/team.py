from src.fantasy.process import Processor
import src.team.utils.combine_bet_fpl as combine_bet_fpl
from src.get_data.connector_sql import PostgresConnector
import pandas as pd

class Team:

    def __init__(self, season, next_gameweek, odds_weight_def=0.6, odds_weight_fwd=0.4): # adjusted from current_gameweek to next_gameweek
        self.season = season
        self.gameweek = next_gameweek
        self.odds_weight_def = odds_weight_def
        self.odds_weight_fwd = odds_weight_fwd
        self.processor = Processor(season, next_gameweek) ## TODO: This should be a processor for both odds and FPL data combined
        self.connector = PostgresConnector()  # Instantiated? Does this need to be yet?

        self.initial_xi = pd.DataFrame()  # Could be another object of the same class? That would be v. nice
        self.first_xi = pd.DataFrame()
        self.first_xv = pd.DataFrame()

    def get_data(self):
        """Run the processor"""
        df_odds = self.connector.get_win_odds(self.season, self.gameweek)  # Adjusted from gameweek+1 to gameweek
        df_players = self.processor.player_stats

        # TODO: Think about how to collect this into a single function - user doesn't care about this detail
        df_next_game = combine_bet_fpl.shape_home_away_fixtures(df_players, df_odds)
        df_next_game = combine_bet_fpl.shape_double_gameweeks(df_next_game)
        df_next_game = combine_bet_fpl.clean_next_game(df_next_game, self.gameweek, self.odds_weight_def, self.odds_weight_fwd)

        return df_next_game

    def pick(self):
        """Run picks"""
        pass

    def suggest_transfers(self):
        pass

    def suggest_specific_transfer(self):
        pass