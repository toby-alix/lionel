from typing import Type
import pandas as pd

from src.connect.combine import BetFPLCombiner
from src.team.select import DumbOptimiser

class Team:

    def __init__(
            self, 
            season, 
            next_gameweek,  # adjusted from current_gameweek to next_gameweek
            df_next_game=pd.DataFrame(), 
            initial_team:Type['Team']=None, # The previous team for updates to be made to
            n_transfers=None,
            odds_weight_def=0.6, 
            odds_weight_fwd=0.4,
            optimisation_obj=DumbOptimiser,
            budget=1000,
            testing=False,
        ): 

        self.season = season
        self.gameweek = next_gameweek
        self.processor = BetFPLCombiner(season, next_gameweek, odds_weight_def, odds_weight_fwd) ## TODO: Team should pull from DB not straight from the scraper.
        self.selector = optimisation_obj

        self.df_next_game = df_next_game
        self.initial_team = initial_team  # Could be another object of the same class? That would be v. nice
        self.n_transfers = n_transfers
        self.first_xi = pd.DataFrame()
        self.first_xv = pd.DataFrame()

        self.budget = budget # TODO: Create class
        self.value = None

        self.selected = False
        self.testing = testing

    def __repr__(self):
        return (f"Team object for GW {self.gameweek} of season {self.season}."
                f" Team selected: {self.selected}.")

    @property
    def selector(self):
        if isinstance(self._selector, type):
            self._selector = self._selector(
                player_df=self.df_next_game, 
                season=self.season, 
                budget=self.budget, 
                initial_team=self.initial_team, 
                testing=self.testing,
            )
        return self._selector
    
    @selector.setter
    def selector(self, val):
        self._selector = val

    @property
    def df_next_game(self):
        """Collects next gameweek data from DB unless 
        it was passed at instantiation"""
        if self._df_next_game.empty:
            self._df_next_game = self.processor.prepare_next_gw()
        return self._df_next_game

    @df_next_game.setter
    def df_next_game(self, val):
        self._df_next_game = val

    @property
    def value(self):
        if self._value is None and not self.selected:
            raise Exception("Team has not been selected.")
        else:
            first_xi = self.first_xi[self.first_xi.picked == 1]
            value = int(first_xi.value.sum())
            self._value = value
        return self._value
    
    
    @value.setter
    def value(self, val):
        self._value = val

    @property
    def budget(self):
        return self._budget
    
    @budget.setter
    def budget(self, val):
        if self.initial_team is None:
            self._budget = val
        else:
            remaining = self._get_deficit_budget()
            budget = self.initial_xi.value
            self._budget = budget

    def _get_deficit_budget(self):
        """Get budget after adjustments for penalties"""
        pass

    def pick_xi(self):
        """Run picks"""
        self.first_xi = self.selector.pick_xi()
        self.selected = True
        return self.first_xi

    def suggest_transfers(self):
        pass

    def suggest_specific_transfer(self):
        pass