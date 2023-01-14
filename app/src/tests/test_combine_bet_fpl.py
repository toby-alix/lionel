import pandas as pd
import json

from app.src.get_data.scrape_fpl import FPLScraper
from app.src.get_data.connector_bet import BetAPIConnector
from app.src.use_data.combine_bet_fpl import combine_bet_fpl


def test_combine_bet_fpl():

    with open(r"H:\3. Github3\lionel-app\app\src\tests\data\test_api_response.json") as f:
        response_dict = json.load(f)
    
    s_bet = BetAPIConnector(response_dict=response_dict)
    df_odds = s_bet.run()

    s_fpl = FPLScraper(23)
    s_fpl.get_season_fixtures()
    df_fixtures = s_fpl.fixtures

    combined = combine_bet_fpl(df_odds, df_fixtures, next_gameweek=20, season=23)

    return combined