import os
from dotenv import dotenv_values
import psycopg2
from sqlalchemy import create_engine
import pandas as pd
import datetime as dt

# TODO: Create functions for filling data from SQL -> Only call if attribute is None
# TODO: Add function to ensure data was uploaded successfully

ENV_VARS = dotenv_values()

class PostgresConnector:

    POSTGRES_USER = os.environ.get('POSTGRES_USER') or ENV_VARS['POSTGRES_USER']
    POSTGRES_PWD = os.environ.get('POSTGRES_PWD') or ENV_VARS['POSTGRES_PWD']
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST') or ENV_VARS['POSTGRES_HOST']
    POSTGRES_DB = os.environ.get('POSTGRES_DB') or ENV_VARS['POSTGRES_DB']
    POSTGRES_URI = os.environ.get('POSTGRES_DB') or ENV_VARS['POSTGRES_DB']
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or ENV_VARS['SQLALCHEMY_DATABASE_URI']


    def __init__(self):
        
        self.dates=pd.DataFrame()
        self.conn = psycopg2.connect(
            host=PostgresConnector.POSTGRES_HOST,
            database=PostgresConnector.POSTGRES_DB,
            user=PostgresConnector.POSTGRES_USER,
            password=PostgresConnector.POSTGRES_PWD,
        )
        self.engine = create_engine(
            PostgresConnector.SQLALCHEMY_DATABASE_URI,
            echo=False,  # Prints all SQL queries -> True for debugging
        )



    def _test_connection(self):
        cur = self.conn.cursor()
        print('PostgreSQL database version:')
        cur.execute('SELECT version()')
        db_version = cur.fetchone()
        print(db_version)
        cur.close()


    def _example_deletion(self):
        """For reference"""
        with self.engine.begin() as con:
            con.exectute('DROP TABLE "example_table"')
        

    def get_win_odds(self, season, gameweek):
        return pd.read_sql(f'SELECT * FROM "WinOdds" WHERE gameweek = {gameweek} AND season = {season}', self.engine)


    def _clean_table_query(self, table, duplicate_cols: list, sort_col):  # Need to catch heisenbug here
        """Deletes duplicated rows based on duplicate cols, chooses the maximum based on sort_col"""
        duplicate_cols = ', '.join(duplicate_cols)
        return f'''
            DELETE FROM "{table}" 
            WHERE {sort_col} IN (
                SELECT {sort_col} FROM "{table}" 
                EXCEPT SELECT MAX({sort_col}) FROM "{table}" 
                GROUP BY {duplicate_cols}
                );
        '''


    def _clean_win_odds(self):
        """Delete duplicates based on all but scrape_time (and gameweek, which is only present for some)"""
        query = self._clean_table_query("WinOdds", ['away', 'game_date', 'home', 'season'], 'scrape_time')
        with self.engine.begin() as con:
            con.execute(query)

        
    def add_new_win_odds(self, df_odds):
        df_odds['scrape_time'] = dt.datetime.now()
        df_odds.to_sql("WinOdds", con=self.engine, if_exists="append", index=False)
        self._clean_win_odds()


    def add_historical_win_odds(self):
        pass

    
    def _clean_team_choices(self):
        query = self._clean_table_query("TeamChoices1", ['name', 'team_name', 'home1', 'away1', 'next_gw'], 'picked_time')
        with self.engine.begin() as con:
            con.execute(query)


    def update_team(self, team):
        team.to_sql("TeamChoices1", self.engine, if_exists='append', index=False)
        self._clean_team_choices()

    
    def get_team(self, next_gameweek, season):
        query = f'SELECT * FROM "TeamChoices1" WHERE next_gw = {next_gameweek} AND season = {season}'
        team = pd.read_sql(query, self.engine) 
        
        if team.empty:
            raise Exception('No players in pulled team. Is it the correct gameweek?')
        
        return team


    def add_gameweek_dates(self, table, df, season):
        query_delete_existing = f"DELETE FROM {table} WHERE season = {season}"
        with self.engine.begin() as con:
            con.execute(query_delete_existing)
        
        df['updated_at'] = dt.datetime.now()
        df.to_sql(table, self.engine, if_exists='append', index=False)


    def _get_dates(self, season=23):
        if len(self.dates) == 0:
            return pd.read_sql(f"SELECT * FROM gameweek_dates WHERE season = {season}", con=self.engine)
        else:
            return self.dates

    
    def get_next_gameweek(self, season):  
        dates = self._get_dates(season)

        event_col_ind = dates.columns.get_loc('gameweek')
        dates['start_last'] = dates['start_last'].dt.date
        next_gameweek = dates[dates['start_last'].ge(dt.date.today())].iloc[0, event_col_ind]
        
        return next_gameweek


    def get_gameweek_status(self, season, next_gameweek) -> bool:
        dates = self._get_dates(season)

        next_gw_start = dates[dates['gameweek'] == next_gameweek]['start_first'].iloc[0]
        previous_gw_end = dates[dates['gameweek'] == next_gameweek-1]['start_last'].iloc[0]  # This would not account for if the current gameweek was ongoing
       
        gameweek_ongoing = (
            dt.date.today() <= previous_gw_end  # If today is before the end of gw
            or dt.datetime.now() >= next_gw_start + dt.timedelta(hours=10)  # if now (datetime) is after 10am on gameweek start date
        )
       
        return gameweek_ongoing


        