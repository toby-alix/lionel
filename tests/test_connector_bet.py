import pytest
import pandas as pd
import json
import pathlib as Path

from app.src.get_data.connector_bet import BetAPIConnector

parent = Path(__file__).parent

# Example input data
with open(parent / "data/test_api_response.json") as f:
    d = json.load(f)


def test_get_response():
    # s = 
    pass


def test_get_teams():
    pass


def test_get_date():
    pass


def test_adjust_odds():
    pass


def test_aggregate_odds():
    pass



if __name__ == "__main__":

    
    
    s = BetAPIConnector()
    s.response = d
    print(s)
    odds = s.run()
    print(odds)
