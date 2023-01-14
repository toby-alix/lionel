import pandas as pd
import datetime as dt

# TODO: Add consistent team naming conventions

class FPLScraper:
    """One scraper instance to be declared per season. An instance to be declared every day, to account for e.g. season fixtures that might change daily."""

    SEASON_MAP = {23:"2022-23", 22: "2021-22", 21: "2020-21", 20: "2019-20", 19: "2018-19"}

    def __init__(self, season):
        self.season = season
        self.team_ids = pd.DataFrame()
        self.fixtures = pd.DataFrame()
        self.df_gw_stats = pd.DataFrame()
        self._df_shaped_fixtures = pd.DataFrame()
        self.gameweek_dates = pd.DataFrame()
        self.next_gameweek = None
    

    def __repr__(self):
        return f"FPL scraper for {FPLScraper.SEASON_MAP[self.season]} as of {dt.date.today()}"
    

    def _get_team_ids(self):
        team_ids = pd.read_csv(f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{FPLScraper.SEASON_MAP[self.season]}/teams.csv")
        team_ids = team_ids.rename(columns={'name':'team', 'id': 'team_id'})
        team_ids = team_ids.replace({'team': {'Man City': 'Manchester City', 'Man Utd': 'Manchester Utd', 'Spurs': 'Tottenham', "Nott'm Forest": "Nottingham"}})
        self.team_ids = team_ids


    def _get_season_fixtures(self):
        """NB: unerlying data for X gameweeks in future is incorrect. It is accurate when it gets closer."""        
        if self.team_ids.empty:
            self._get_team_ids()
        
        # if not self.df_gw_stats.empty:
        #     return self.df_gw_stats

        fixtures = pd.read_csv(f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{FPLScraper.SEASON_MAP[self.season]}/fixtures.csv")

        fixtures = fixtures.merge(self.team_ids, left_on='team_a', right_on='team_id', how='left')
        fixtures = fixtures.merge(self.team_ids, left_on='team_h', right_on='team_id', how='left')
        
        # Cleaning
        fixtures = fixtures.rename({'team_x': 'away_team_name', 'team_y': 'home_team_name'}, axis=1)
        fixtures = fixtures.drop(['team_id_x', 'team_id_y'], axis=1)

        # Add home/away representation
        fixtures = fixtures.rename({'home_team_name': 'home', 'away_team_name': 'away', 'kickoff_time': 'game_date', 'event': 'gameweek'}, axis=1)
        fixtures[['home', 'away']] = fixtures[['home', 'away']].apply(lambda col: col.str.strip(), axis=1)
        fixtures['game_date'] = pd.to_datetime(fixtures['game_date']).dt.date
        fixtures['game_date'] = pd.to_datetime(fixtures['game_date'])  # Weirdly this has to be doubled to isolate the date aspect as datetime instead of object :/
        fixtures = fixtures[['home', 'away', 'game_date', 'gameweek']]
        self.fixtures = fixtures


    def get_season_fixtures(self):
        if self.fixtures.empty:
            self._get_season_fixtures()
        return self.fixtures


    def _get_gw_stats(self):
        
        # TODO: Check if this column filter works for older seasons or if I need to change it
        # TODO: Consider -> Using a database would helpfully enforce data validation for these columns 
        gw_stats_current = pd.read_csv(f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{FPLScraper.SEASON_MAP[self.season]}/gws/merged_gw.csv")
        gw_stats_previous = pd.read_csv(f"https://raw.githubusercontent.com/vaastav/Fantasy-Premier-League/master/data/{FPLScraper.SEASON_MAP[self.season-1]}/gws/merged_gw.csv")
        
        # Add previous season so that early games can pull from previous seasons
        gw_stats_current['season'] = self.season 
        gw_stats_previous['season'] = self.season-1

        gw_stats = gw_stats_current.append(gw_stats_previous)
        gw_stats['team_id'] = 99
        gw_stats = gw_stats.rename(columns={'team': 'team_name', 'GW': 'gameweek', 'kickoff_time': 'game_date'})

        MAP_ = {
            'team_name': {'Man City': 'Manchester City', 'Man Utd': 'Manchester Utd', 'Spurs': 'Tottenham', "Nott'm Forest": "Nottingham"}, 
            'name': {'Son Heung-min': "Heung-Min Son", 'João Cancelo' :'João Pedro Cavaco Cancelo', 'Emerson Leite de Souza Junior': 'Emerson Aparecido Leite de Souza Junior'}
        }

        gw_stats = gw_stats.replace(MAP_)
        gw_stats['game_date'] = pd.to_datetime(gw_stats['game_date']).dt.date
        gw_stats['game_date'] = pd.to_datetime(gw_stats['game_date'])

        NEEDED_COLS = [
            'gameweek', "assists", "bps", "creativity", "element", "goals_scored", 
            "ict_index", "influence", "minutes", "name", "opponent_team", "position", 
            "season", "selected",  "team_a_score", "team_h_score", "team_id", "team_name", "threat", 
            "total_points", "transfers_balance", "value", "was_home", 'game_date'
        ]

        gw_stats = gw_stats[[col for col in gw_stats.columns if col in NEEDED_COLS]]
        self.df_gw_stats = gw_stats


    def get_gw_stats(self): 
        if self.df_gw_stats.empty:
            self._get_gw_stats()
        return self.df_gw_stats


    def get_next_fixtures(self, next_gameweek):
        if self.fixtures.empty:
            self.get_season_fixtures()
        
        return self.fixtures[self.fixtures['gameweek'] == next_gameweek]
        
        
    def get_gameweek_dates(self):
        if self.fixtures.empty:
            self.get_season_fixtures()
        
        first_kickoff = self.fixtures.groupby('gameweek')[['game_date']].first()
        first_kickoff = first_kickoff.rename(columns={'game_date': 'start_first'})
        last_kickoff = self.fixtures.groupby('gameweek')[['game_date']].last()
        last_kickoff = last_kickoff.rename(columns={'game_date': 'start_last'})
        df_kickoff = pd.concat([first_kickoff, last_kickoff], axis=1).reset_index()
        df_kickoff['season'] = self.season
        
        self.gameweek_dates = df_kickoff

    
    def get_actual_points(self):
        if self.df_gw_stats.empty:
            self.get_gw_stats()
        pass