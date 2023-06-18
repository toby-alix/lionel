from process.fantasy import FPLProcessor
from connect.db import PostgresConnector
from scrape.bet.scrape import FutureBetScraper 
from team.team import Team

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
    team = Team(season, next_gameweek)
    xi = team.pick_xi()
    xi.to_sql("TeamChoices1", con=con.engine, if_exists="append", index=False)
