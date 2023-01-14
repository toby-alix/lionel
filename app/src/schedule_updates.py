from apscheduler.schedulers.background import BackgroundScheduler
import datetime as dt
import numpy as np

import app.src.get_data.connector as connector
import app.src.get_data.scrape_fpl as scrape_fpl
import app.src.get_data.connector_bet as connector_bet
import app.src.use_data.choose_team as choose_team
import app.src.use_data.combine_bet_fpl as combine_bet_fpl


def run_updates(connector_: connector.PostgresConnector, season: int=23):

    scraper_fpl = scrape_fpl.FPLScraper(season) # Create new scraper instance each day so that changes to e.g. fixtures are accounted for
    scraper_fpl.get_gameweek_dates()
    fixtures = scraper_fpl.fixtures
    assert not fixtures.empty

    gameweek_dates = scraper_fpl.gameweek_dates
    connector_.add_gameweek_dates('gameweek_dates', gameweek_dates, season)

    # Check gameweek dates. If gameweek is not ongoing, update win odds and team 
    next_gameweek = connector_.get_next_gameweek(season)
    gameweek_ongoing = connector_.get_gameweek_status(season, next_gameweek)

    if not gameweek_ongoing:

        print('Updating for gameweek:', next_gameweek)

        connector_bet_ = connector_bet.BetAPIConnector()
        df_odds = connector_bet_.run()

        df_odds = combine_bet_fpl.combine_bet_fpl(
            df_odds=df_odds, df_fixtures=fixtures,
            next_gameweek=next_gameweek, season=season,
        )
        
        connector_.add_new_win_odds(df_odds) 

        # Re-run team selection, add it to DB
        team = choose_team.Team(season=season, gameweek=next_gameweek-1, scraper_fpl=scraper_fpl)  # TODO: In this func, for some reason it's not converting 0 to NA, which it should.
        team.pick_xi(connector)

        connector_.update_team(team.first_xi)
    

# Change operation based on being run as __main__ or imported as a module
connector_ = connector.PostgresConnector()
season = 23

if __name__ == "__main__":
    run_updates(connector_, season)

else:
    print("Starting scheduler")
    sched = BackgroundScheduler()
    sched.add_job(run_updates, args=[connector_, season], trigger='cron', year='*', month='*', day_of_week='*', hour="7")
    sched.start()
