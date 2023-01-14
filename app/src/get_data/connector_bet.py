import numpy as np
import datetime as dt
import pandas as pd
import re
import os
import requests
from dotenv import dotenv_values


# Another potential API to use: https://www.programmableweb.com/api/premier-league-live-scores-rest-api-v20#:~:text=The%20Premier%20League%20Live%20Scores,result%20using%20an%20AI%20Deep
## AIrsenal scrapes understat: https://github.com/alan-turing-institute/AIrsenal/blob/main/airsenal/scraper/scrape_understat.py
# Whether to use classes: https://medium.com/@senchooo/build-oop-program-with-scraping-feature-in-python-chapter-1-design-your-program-with-oop-aec82eb1d4b1


ENV_VARS = dotenv_values()
API_KEY = os.environ.get('API_KEY') or ENV_VARS['API_KEY']


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
        games = BetAPIConnector._rename_teams(games)
    
        games['game_date'] = pd.to_datetime(games['game_date']).dt.date
        games['game_date'] = pd.to_datetime(games['game_date'])

        return games


    