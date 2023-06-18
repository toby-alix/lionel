import datetime as dt

from src.process.fantasy.process import FPLProcessor
from src.process.db.connector import PostgresConnector
from src.scrape.bet.connector_bet import BetAPIConnector #TODO 


def run(season, next_gameweek):
    
    con = PostgresConnector()
    
    fpl_processor = FPLProcessor(season, next_gameweek)
    player_stats = fpl_processor.player_stats

    player_stats.to_sql("PlayerStats", con=con.engine, if_exists="append", index=False)

    win_odds = BetAPIConnector.run()  # TODO
    con.add_new_win_odds(win_odds)


    