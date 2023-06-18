import pandas as pd
import numpy as np
import datetime as dt

pd.options.mode.chained_assignment = None  # default='warn'

class Game:
    """
    Takes a game dictionary and makes it usable
    """

    def __init__(self, game_dict: dict):
        self.game_dict = game_dict
        self.bookmakers = []
        self.raw_odds = pd.DataFrame()
        self.adjusted_odds = pd.DataFrame()
        self.home_team = ''
        self.away_team = ''
        self.date = dt.date
        self.aggregated_odds = {}
        
        self.run()


    def get_teams(self, game: dict=None) -> dict:
        
        # Allow game to be passed for testing
        if self.home_team != '':
            pass

        else:
            game = game or self.game_dict 
        
            self.home_team = game['home_team']
            self.away_team = game['away_team']

        return {'home_team': self.home_team, 'away_team': self.away_team}


    def get_game_date(self, game: dict=None) -> dt.date:
        game = game or self.game_dict 
        date = dt.datetime.strptime(game['commence_time'],"%Y-%m-%dT%H:%M:%SZ").date()
        self.date = date
        return date


    @staticmethod
    def _get_odds_for_one_bookie(odds_list, home_team, away_team):
        home_odds = [1/d['price'] for d in odds_list if d['name'] == home_team][0]
        away_odds = [1/d['price'] for d in odds_list if d['name'] == away_team][0]
        draw_odds = [1/d['price'] for d in odds_list if d['name'] == 'Draw'][0]
        return {'home_odds': home_odds, 'away_odds': away_odds, 'draw_odds': draw_odds}    
    

    def _format_one_bookies_data(self, bookie, home_team, away_team):
        name = bookie['key']
        update = bookie['last_update']
        odds_list = bookie['markets'][0]['outcomes']
        odds_dict = self._get_odds_for_one_bookie(odds_list, home_team, away_team)
        
        out = {'home_team': home_team, 'away_team': away_team, 
               'bookmaker': name, 'updated_at': update}
        out.update(odds_dict)
        return out


    def get_raw_odds(self, game: dict=None) -> pd.DataFrame:
        game = game or self.game_dict
        bookies_list = game['bookmakers']
        teams = self.get_teams(game)

        formatted_bookies = []
        for bookie in bookies_list:
            single_bookie_formatted = self._format_one_bookies_data(
                bookie, home_team=teams['home_team'], 
                away_team=teams['away_team']
            )
            formatted_bookies.append(single_bookie_formatted)
            
        df_raw_odds = pd.DataFrame.from_dict(formatted_bookies)
        self.raw_odds = df_raw_odds
        return df_raw_odds


    @staticmethod
    def _adjust_raw_game_odds_for_margin(raw_odds: pd.Series) -> pd.Series:
       
        total_odds = raw_odds['home_odds'] + raw_odds['away_odds'] + raw_odds['draw_odds']
    
        raw_odds['home_odds'] = raw_odds['home_odds']/total_odds
        raw_odds['away_odds'] = raw_odds['away_odds']/total_odds
        raw_odds['draw_odds'] = raw_odds['draw_odds']/total_odds
        return raw_odds


    def adjust_raw_odds_df_for_margin(self, raw_odds_df: pd.DataFrame=None) -> pd.DataFrame:
        raw_odds_df = raw_odds_df or self.raw_odds
        adjusted_odds_df = raw_odds_df.apply(lambda row: self._adjust_raw_game_odds_for_margin(row), axis=1)
        self.adjusted_odds = adjusted_odds_df
        return self.adjusted_odds  

    
    def run(self):
        self.get_teams()
        self.get_game_date()
        self.get_raw_odds()
        self.adjust_raw_odds_df_for_margin()