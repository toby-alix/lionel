import numpy as np
import datetime as dt
import pandas as pd
import re
import os
import requests
from dotenv import dotenv_values

ENV_VARS = dotenv_values()
API_KEY = os.environ.get('API_KEY') or ENV_VARS['API_KEY']

api_url = "https://api.the-odds-api.com/v4/sports/soccer_epl/odds/?apiKey=c7d79004e7018b5ef05080044a0f04ca&regions=uk&markets=h2h"

# NB: GET for historical odds GET /v4/sports/{sport}/odds-history/?apiKey={apiKey}&regions={regions}&markets={markets}&date={date}
# Date needs to be in timestamp format: 2021-10-18T12:00:00Z
# Another potential API to use: https://www.programmableweb.com/api/premier-league-live-scores-rest-api-v20#:~:text=The%20Premier%20League%20Live%20Scores,result%20using%20an%20AI%20Deep

## AIrsenal scrapes understat: https://github.com/alan-turing-institute/AIrsenal/blob/main/airsenal/scraper/scrape_understat.py
# Whether to use classes: https://medium.com/@senchooo/build-oop-program-with-scraping-feature-in-python-chapter-1-design-your-program-with-oop-aec82eb1d4b1


class BetAPIConnector():

    BASE_URL = f"https://api.the-odds-api.com//v4/sports/"
    

    def __init__(
        self,
        sport="soccer_epl",
        regions="uk",
        markets="h2h",  # also spreads, totals, outrights
        api_key=API_KEY,
        response_dict=None,  # Enable passing a response for testing
        date=None
    ):
        # Inputs
        self.sport = sport
        self.regions = regions
        self.markets = markets
        self.date = self._format_date(date)
        
        # API Endpoints
        self.odds_endpoint = BetAPIConnector.BASE_URL + f"{sport}/odds/?apiKey={api_key}&regions={regions}&markets={markets}"    
        self.sports_endpoint=BetAPIConnector.BASE_URL + f"?apiKey={api_key}"
        self.historical_endpoint=BetAPIConnector.BASE_URL + f"{sport}/odds-history/?apiKey={api_key}&regions={regions}&markets={markets}&date={self.date}"
        
        # Repsponse parts
        self.response_dict = response_dict
        self.headers = None
        self.status = None


    def _format_date(self, date):
        """ Formats the date for the API historical request

        Args:
            date (str): Date in YYMMDD format

        Returns:
            _type_: Date in 20YY-MM-DDT12:00:00Z format
        """
        if date is None:
            return None
        else:
            assert len(date) == 6
            return f"20{date[:2]}-{date[2:4]}-{date[4:]}T12:00:00Z"


    @staticmethod
    def _check_response():
        # return response.ok
        # do something based on response code
        pass


    @staticmethod
    def _get_reason_for_failure():
        pass


    def get_future_response(self):
        self._get_response(self.odds_endpoint)


    def get_hist_response(self):
        self._get_response(self.historical_endpoint)


    def _get_response(self, url) -> list:
        if self.response_dict is None:
            try:
                r = requests.get(url)
                assert r.ok
                self.headers = r.headers
                self.status = r.status_code
                self.response_dict = r.json()
            except:
                print("Uh oh. Something to update")


    @staticmethod
    def get_teams(game) -> dict:
        # home = game['home_team']
        # away = game['away_team']
        return {'home': game['home_team'], 'away': game['away_team']}


    @staticmethod
    def get_date(game):
        date = dt.datetime.strptime(game['commence_time'],"%Y-%m-%dT%H:%M:%SZ").date()
        # print(date, type(date))
        return date


    @staticmethod
    def _adjust_single_bookie_for_margin(single_bookies_odds: dict):
        """Takes odds for a single bookmakers, adjusts the odds at to sum to 1

        Args:
            sub_dict_ (dict): _description_

        Returns:
            _type_: _description_
        """
        outcomes = single_bookies_odds['markets'][0]['outcomes']  # Each bookmaker offers multiple markets (e.g. h2h, spread)
        total_price = sum([1/d['price'] for d in outcomes])
        adjusted_dict = [{'name': d['name'], 'price': (1/(d['price']))/total_price} for d in outcomes]  # Adjust the odds by the margin expect by bookie -> then odds sum to 1
        return adjusted_dict


    @staticmethod
    def adjust_odds_list_for_margin(game: dict) -> list:
        """Takes game dictionary, filters odds and adjusts them to probabilities that sum to 1.

        Args:
            game (dict): Dictonary of game from list response from API.

        Returns:
            list: Dictionaries of format {'home_odds': home_odds, 'away_odds': away_odds, 'draw_odds': draw_odds}  
        """
        bookies_list = game['bookmakers']
        adjusted_odds_list = []

        for single_bookies_odds in bookies_list:
            adjusted_dict = BetAPIConnector._adjust_single_bookie_for_margin(single_bookies_odds)
            adjusted_odds_list.append(adjusted_dict)
        
        return adjusted_odds_list


    @staticmethod
    def aggregate_odds(odds_list: list, home_team: str, away_team: str) -> dict:
        """_summary_

        Args:
            odds_list (list): List of dictonaries of odds returned from _adjust_odds_list_for_margin
            home_team (str):
            away_team (str): 

        Returns:
            dict: Mean odds in format {'home_odds': home_odds, 'away_odds': away_odds, 'draw_odds': draw_odds} 
        """
        home_odds = np.mean([[d['price'] for d in l if d['name'] == home_team] for l in odds_list])
        away_odds = np.mean([[d['price'] for d in l if d['name'] == away_team] for l in odds_list])
        draw_odds = np.mean([[d['price'] for d in l if d['name'] == 'Draw'] for l in odds_list])
        return {'home_odds': home_odds, 'away_odds': away_odds, 'draw_odds': draw_odds}       


    @staticmethod
    def _rename_teams(df_games):
        name_map = {
            'Manchester United': 'Manchester Utd', 'Tottenham Hotspur': 'Tottenham', "Nottingham Forest": "Nottingham",
            'Brighton and Hove Albion': 'Brighton', 'Leicester City': 'Leicester',
            'Leeds United': 'Leeds', 'Newcastle United': 'Newcastle', 'West Ham United': 'West Ham',
            'Wolverhampton Wanderers': 'Wolves',
        } 
        return df_games.replace({'home': name_map, 'away': name_map})


    ## Can this be a decorator or something
    def run(self):
        self.get_future_response()
        games = []
        for game in self.response_dict:

            game_dict = {}

            # Format data from the response
            teams = self.get_teams(game)
            date = {'game_date': self.get_date(game)}
            adjusted_odds = self.adjust_odds_list_for_margin(game)
            aggregated_odds = self.aggregate_odds(adjusted_odds, teams['home'], teams['away'])

            game_dict.update(teams)
            game_dict.update(date)
            game_dict.update(aggregated_odds)

            games.append(game_dict)
        
        games = pd.DataFrame.from_dict(games)
    
        games['game_date'] = pd.to_datetime(games['game_date']).dt.date
        games['game_date'] = pd.to_datetime(games['game_date'])
        
        games = BetAPIConnector._rename_teams(games)

        return games


    

"""
A single game obj looks like this:

{'id': '3c4512761cfd2e1782bb85271764ccaf',
 'sport_key': 'soccer_epl',
 'sport_title': 'EPL',
 'commence_time': '2023-01-13T20:00:00Z',
 'home_team': 'Aston Villa',
 'away_team': 'Leeds United',
 'bookmakers': [{'key': 'paddypower',
   'title': 'Paddy Power',
   'last_update': '2023-01-12T22:39:49Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:49Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.9},
      {'name': 'Leeds United', 'price': 4.0},
      {'name': 'Draw', 'price': 3.5}]}]},
  {'key': 'virginbet',
   'title': 'Virgin Bet',
   'last_update': '2023-01-12T22:39:50Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:50Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.95},
      {'name': 'Leeds United', 'price': 4.0},
      {'name': 'Draw', 'price': 3.6}]}]},
  {'key': 'livescorebet',
   'title': 'LiveScore Bet',
   'last_update': '2023-01-12T22:40:00Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:40:00Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.95},
      {'name': 'Leeds United', 'price': 4.0},
      {'name': 'Draw', 'price': 3.6}]}]},
  {'key': 'betway',
   'title': 'Betway',
   'last_update': '2023-01-12T22:40:17Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:40:17Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.91},
      {'name': 'Leeds United', 'price': 4.0},
      {'name': 'Draw', 'price': 3.6}]}]},
  {'key': 'sport888',
   'title': '888sport',
   'last_update': '2023-01-12T22:39:59Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:59Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.91},
      {'name': 'Leeds United', 'price': 3.95},
      {'name': 'Draw', 'price': 3.6}]}]},
  {'key': 'williamhill',
   'title': 'William Hill',
   'last_update': '2023-01-12T22:39:59Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:59Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.95},
      {'name': 'Leeds United', 'price': 3.9},
      {'name': 'Draw', 'price': 3.5}]}]},
  {'key': 'betvictor',
   'title': 'Bet Victor',
   'last_update': '2023-01-12T22:39:53Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:53Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.9},
      {'name': 'Leeds United', 'price': 3.9},
      {'name': 'Draw', 'price': 3.5}]}]},
  {'key': 'skybet',
   'title': 'Sky Bet',
   'last_update': '2023-01-12T22:38:22Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:38:22Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.91},
      {'name': 'Leeds United', 'price': 3.8},
      {'name': 'Draw', 'price': 3.6}]}]},
  {'key': 'betfair',
   'title': 'Betfair',
   'last_update': '2023-01-12T22:43:21Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:43:21Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.99},
      {'name': 'Leeds United', 'price': 4.3},
      {'name': 'Draw', 'price': 3.7}]},
    {'key': 'h2h_lay',
     'last_update': '2023-01-12T22:43:21Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 2.0},
      {'name': 'Leeds United', 'price': 4.4},
      {'name': 'Draw', 'price': 3.75}]}]},
  {'key': 'boylesports',
   'title': 'BoyleSports',
   'last_update': '2023-01-12T22:39:49Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:49Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.87},
      {'name': 'Leeds United', 'price': 4.0},
      {'name': 'Draw', 'price': 3.5}]}]},
  {'key': 'mrgreen',
   'title': 'Mr Green',
   'last_update': '2023-01-12T22:39:49Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:49Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.83},
      {'name': 'Leeds United', 'price': 4.25},
      {'name': 'Draw', 'price': 3.75}]}]},
  {'key': 'casumo',
   'title': 'Casumo',
   'last_update': '2023-01-12T22:39:49Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:49Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.8},
      {'name': 'Leeds United', 'price': 4.1},
      {'name': 'Draw', 'price': 3.65}]}]},
  {'key': 'unibet_uk',
   'title': 'Unibet',
   'last_update': '2023-01-12T22:40:00Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:40:00Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.85},
      {'name': 'Leeds United', 'price': 4.25},
      {'name': 'Draw', 'price': 3.75}]}]},
  {'key': 'leovegas',
   'title': 'LeoVegas',
   'last_update': '2023-01-12T22:39:24Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:24Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.82},
      {'name': 'Leeds United', 'price': 4.2},
      {'name': 'Draw', 'price': 3.7}]}]},
  {'key': 'coral',
   'title': 'Coral',
   'last_update': '2023-01-12T22:39:49Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:39:49Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.91},
      {'name': 'Leeds United', 'price': 3.9},
      {'name': 'Draw', 'price': 3.6}]}]},
  {'key': 'ladbrokes',
   'title': 'Ladbrokes',
   'last_update': '2023-01-12T22:38:21Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:38:21Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.91},
      {'name': 'Leeds United', 'price': 3.8},
      {'name': 'Draw', 'price': 3.5}]}]},
  {'key': 'matchbook',
   'title': 'Matchbook',
   'last_update': '2023-01-12T22:40:00Z',
   'markets': [{'key': 'h2h',
     'last_update': '2023-01-12T22:40:00Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 1.99},
      {'name': 'Leeds United', 'price': 4.3},
      {'name': 'Draw', 'price': 3.7}]},
    {'key': 'h2h_lay',
     'last_update': '2023-01-12T22:40:00Z',
     'outcomes': [{'name': 'Aston Villa', 'price': 2.0},
      {'name': 'Leeds United', 'price': 4.4},
      {'name': 'Draw', 'price': 3.75}]}]}]}
"""