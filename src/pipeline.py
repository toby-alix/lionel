import datetime as dt

from src.process.fantasy import FPLProcessor
from src.connect.db import PostgresConnector
from src.scrape.bet.scrape import FutureBetScraper 


def run(season, next_gameweek):
    
    con = PostgresConnector()
    
    # Update FPL stats and add them to DB
    fpl_processor = FPLProcessor(season, next_gameweek)
    player_stats = fpl_processor.player_stats
    player_stats.to_sql("PlayerStats", con=con.engine, if_exists="append", index=False)

    # Update betting odds and add to DB
    bet_scraper = FutureBetScraper()
    bet_scraper.run_scrape()
    win_odds = bet_scraper.to_df()
    con.add_new_win_odds(win_odds)

    # Update team choices and add them to DB
    pass


    