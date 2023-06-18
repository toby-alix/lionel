import os
from dotenv import dotenv_values
import psycopg2
from sqlalchemy import create_engine
import pandas as pd


ENV_VARS = dotenv_values()

class PostgresConnector:

    POSTGRES_USER = os.environ.get('POSTGRES_USER') or ENV_VARS['POSTGRES_USER']
    POSTGRES_PWD = os.environ.get('POSTGRES_PWD') or ENV_VARS['POSTGRES_PWD']
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST') or ENV_VARS['POSTGRES_HOST']
    POSTGRES_DB = os.environ.get('POSTGRES_DB') or ENV_VARS['POSTGRES_DB']
    SQLALCHEMY_DATABASE_URI = os.environ.get('SQLALCHEMY_DATABASE_URI') or ENV_VARS['SQLALCHEMY_DATABASE_URI']

    def __init__(self):
        
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

    def query(self, query):
        with self.engine.begin() as con:
            con.execute(query)

    # Specific queries don't really belong here...
    def get_win_odds(self, season, gameweek):
        return pd.read_sql(f'SELECT * FROM "WinOdds" WHERE gameweek = {gameweek} AND season = {season}', self.engine)

    def get_player_stats(self, season, gameweek):
        return pd.read_sql(f'SELECT * FROM "PlayerStats" WHERE gameweek = {gameweek} AND season = {season}', self.engine)
