"""
Add gameweek dates to odds taken from the API
"""

import pandas as pd


def combine_bet_fpl(df_odds: pd.DataFrame, df_fixtures: pd.DataFrame, next_gameweek:int, season: int=23) -> pd.DataFrame:
    
    df_fixtures = df_fixtures[df_fixtures['gameweek'] == next_gameweek]
    df_odds = df_odds.merge(df_fixtures, how='right', on=['home', 'away', 'game_date'], indicator=False)
    df_odds['season'] = season
    return df_odds
