from src.scrape.bet.game import Game

import numpy as np
import datetime as dt
import pandas as pd
import os
import requests
from dotenv import dotenv_values
from abc import ABCMeta, abstractmethod

ENV_VARS = dotenv_values()

class BetScraper(metaclass=ABCMeta):

    BASE_URL = f"https://api.the-odds-api.com//v4/sports/"
    SPORT = "soccer_epl"
    REGIONS = "uk"
    MARKETS="h2h"
    API_KEY = os.environ.get('API_KEY') or ENV_VARS['API_KEY']

    def __init__(
        self,
    ):

        # API Endpoints
        self.sports_endpoint=BetScraper.BASE_URL + f"?apiKey={BetScraper.API_KEY}"
        self.games = []

    @property
    @abstractmethod
    def odds_endpoint(self):
        pass
    
    def _get_response(self, url) -> list:
        try:
            r = requests.get(url)
            assert r.ok
            return r
        except:
            print("Uh oh. Something to update")

    def run_scrape(self):
        response = self._get_response(self.odds_endpoint)
        response_dict = response.json()
        games = [Game(game_dict) for game_dict in response_dict]
        self.games.extend(games)
        return games
    
    def games_to_df(self):
        if len(self.games) == 0:
            raise Exception("Run the scrape first")
        
        df = pd.DataFrame.from_dict([game.to_dict() for game in self.games])
        return df        
    
    
class FutureBetScraper(BetScraper):
    def __init__(self):
        BetScraper.__init__(self)

    @property
    def odds_endpoint(self):
        return (
            BetScraper.BASE_URL
            + f"{BetScraper.SPORT}/odds/?apiKey={BetScraper.API_KEY}&"
            f"regions={BetScraper.REGIONS}&markets={BetScraper.MARKETS}"
        )
    

class HistoricalBetScraper(BetScraper):
    def __init__(self, date):
        BetScraper.__init__(self)
        self.date = date
        
    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, val):
        try:
            assert len(val) == 6
            self._date = f"20{val[:2]}-{val[2:4]}-{val[4:]}T12:00:00Z"
        except:
            raise Exception("Date must be a str of YYMMDD")

    @property
    def odds_endpoint(self):
        return (
            BetScraper.BASE_URL 
            + f"{BetScraper.SPORT}/odds-history/?apiKey="
            f"{BetScraper.API_KEY}&regions={BetScraper.REGIONS}&markets={BetScraper.MARKETS}&date={self.date}"
        )
    
