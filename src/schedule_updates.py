from apscheduler.schedulers.background import BackgroundScheduler
import numpy as np

import app.src.get_data.connector_sql as connector_sql
import app.src.get_data.connector_fpl as connector_fpl
import app.src.get_data.connector_bet as connector_bet
import app.src.use_data.choose_team as choose_team
import app.src.use_data.combine_bet_fpl as combine_bet_fpl


def run_updates(connector_: connector_sql.PostgresConnector, season: int=23):

    scraper_fpl = connector_fpl.FPLScraper(season)
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
        team = choose_team.Team(season=season, gameweek=next_gameweek-1, scraper_fpl=scraper_fpl) 
        team.pick_xi(connector_)

        connector_.update_team(team.first_xi)
    

connector_ = connector_sql.PostgresConnector()
season = 23

run_updates(connector_, season)
print("Starting scheduler")
sched = BackgroundScheduler()
sched.add_job(run_updates, args=[connector_, season], trigger='cron', year='*', month='*', day_of_week='*', hour="7")
sched.start()
