from typing import Type
import pandas as pd

from src.process.combine import BetFPLCombiner
from src.team.select import Optimiser

class Team:

    def __init__(
            self, 
            season, 
            next_gameweek,  # adjusted from current_gameweek to next_gameweek
            df_next_game=pd.DataFrame(), 
            initial_xi:Type['Team']=None, # The previous team for updates to be made to
            odds_weight_def=0.6, 
            odds_weight_fwd=0.4
        ): 
        self.season = season
        self.gameweek = next_gameweek
        self.processor = BetFPLCombiner(season, next_gameweek, odds_weight_def, odds_weight_fwd) ## TODO: Team should pull from DB not straight from the scraper.
        self.selector = Optimiser
       
        self.df_next_game = df_next_game
        self.initial_xi = initial_xi  # Could be another object of the same class? That would be v. nice
        self.first_xi = pd.DataFrame()
        self.first_xv = pd.DataFrame()

    @property
    def selector(self):
        if isinstance(self._selector, type):
            self._selector = self._selector(self.df_next_game, self.season, budget=1000, testing=False)
        return self._selector
    
    @selector.setter
    def selector(self, val):
        self._selector = val

    @property
    def df_next_game(self):
        if self._df_next_game.empty:
            self._df_next_game = self.processor.prepare_next_gw()
        return self._df_next_game

    @df_next_game.setter
    def df_next_game(self, val):
        self._df_next_game = val

    def pick_xi(self):
        """Run picks"""
        self.first_xi = self.selector.pick_xi()
        return self.first_xi

    def suggest_transfers(self):
        pass

    def suggest_specific_transfer(self):
        pass