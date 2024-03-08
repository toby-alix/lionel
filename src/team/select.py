import numpy as np
import datetime as dt
import pandas as pd
from pulp import LpVariable, LpProblem, lpSum, LpMaximize
from abc import ABCMeta, abstractmethod


class Optimiser(metaclass=ABCMeta):

    POS_CONSTRAINTS = {
        "XV": {
            "DEF": [5],
            "FWD": [3],
            "MID": [5],
            "GK": [2],
        },
        "XI": {
            "DEF": [5, 3],
            "FWD": [3, 1],
            "MID": [5, 2],
            "GK": [1, 1],
        },
    }

    def __init__(self, player_df, season, budget, testing=False):
        self.player_df = player_df.fillna(0).reset_index()
        self.teams = self.player_df.team_name.to_list()
        self.positions = self.player_df.position.to_list()
        self.total_points = self.player_df.total_points.to_list()
        self.points_weighted = self.player_df.points_weighted.to_list()
        self.season = season

        self.budget = budget
        self.testing = testing

        self.first_xv = pd.DataFrame()
        self.first_xi = pd.DataFrame()

    @abstractmethod
    def pick_xi(self):
        """Return df of all players with first_xi == 1 for those that are picked"""
        pass


class DumbOptimiser(Optimiser):

    def __init__(
        self, player_df, season, budget=1000, testing=False, max_var="value_fixture"
    ):
        Optimiser.__init__(self, player_df, season, budget, testing)

        self.max_var = max_var
        self.players = None
        self.captains = None
        self.changes = None

    def _create_decision_var(self, prefix):
        return [LpVariable(prefix + str(i), cat="Binary") for i in self.player_df.index]

    @property
    def players(self):
        if self._players is None:
            self._players = self._create_decision_var("player_")
        return self._players

    @players.setter
    def players(self, val):
        self._players = val

    @property
    def captains(self):
        if self._captains is None:
            self._captains = self._create_decision_var("captain_")
        return self._captains

    @captains.setter
    def captains(self, val):
        self._captains = val

    @property
    def changes(self):
        if self._changes is None:
            self._changes = self._create_decision_var("change_")
        return self._changes

    @changes.setter
    def changes(self, val):
        self._changes = val

    @property
    def first_xv(self):
        if self._first_xv.empty:
            self._first_xv = self._pick_xv()
        return self._first_xv

    @first_xv.setter
    def first_xv(self, val):
        self._first_xv = val

    def _add_budget_constraints(self, prob):
        prob += (
            lpSum(
                self.players[i] * self.player_df.value[self.player_df.index[i]]
                for i in range(len(self.player_df))
            )
            <= self.budget
        )
        return prob

    def _add_club_constraints(self, prob):
        for club in self.teams:
            prob += (
                lpSum(
                    self.players[i]
                    for i in range(len(self.player_df))
                    if self.teams[i] == club
                )
                <= 3
            )

        return prob

    # will this work for the update?
    def _add_xv_constraints(self, prob):
        prob += sum(self.players) == 15  # can't believe i missed these lol
        prob = self._add_budget_constraints(prob)
        prob += sum(self.captains) == 1  # can't believe i missed these lol
        prob = self._add_position_constraints(prob, self.players, self.player_df, "XV")
        prob = self._add_club_constraints(prob)
        for i in range(len(self.player_df)):
            prob += (self.players[i] - self.captains[i]) >= 0
        return prob

    def _add_changes_constraint(self, prob, max_changes):
        prob += (
            lpSum(
                self.changes[i]
                for i in range(len(self.player_df))
                if self.player_df["initial_team"][i]
            )
        ) >= 15 - max_changes
        return prob

    def _add_update_constraints(self, probs):
        pass

    def _clean_xv(self, indices, captain_index):
        team_2 = self.player_df.copy(deep=True)
        team_2.loc[indices, "picked"] = 1
        team_2.loc[team_2["picked"] != 1, "picked"] = 0
        team_2["captain"] = 0
        team_2.loc[captain_index, "captain"] = 1
        team_2 = team_2.drop("index", axis=1).reset_index()
        return team_2

    @staticmethod
    def _player_indices(players):
        players = [player for player in players if player.varValue != 0]
        indices = [int(player.name.split("_")[1]) for player in players]
        return indices

    @staticmethod
    def _captain_index(captains):
        captain = [player for player in captains if player.varValue != 0]
        captain_index = int(captain[0].name.split("_")[1])
        return captain_index

    def _pick_xv(self):
        prob = LpProblem("FPL Player Choices", LpMaximize)
        prob += lpSum(
            (self.players[i] + self.captains[i]) * self.player_df["points_weighted"][i]
            for i in range(len(self.player_df))
        )

        # Add constraints and solve
        prob = self._add_xv_constraints(prob)
        prob.solve()

        # Get indices of selected players and captain
        indices = self._player_indices(self.players)
        captain_index = self._captain_index(self.captains)
        team = self._clean_xv(indices, captain_index)
        return team

    def _add_position_constraints(self, prob, players, df, xi_xv="XV"):
        positions = df.position.to_list()
        for pos in ["GK", "DEF", "MID", "FWD"]:
            # add upper bound for position (for XV this is effectively an equality bound)
            prob += (
                lpSum(players[i] for i in range(len(df)) if positions[i] == pos)
                <= self.POS_CONSTRAINTS[xi_xv][pos][0]
            )
            # If first team, add lower bound for the position
            if xi_xv == "XI":
                prob += (
                    lpSum(players[i] for i in range(len(df)) if positions[i] == pos)
                    >= self.POS_CONSTRAINTS[xi_xv][pos][1]
                )
        return prob

    # clean this up, not great
    def _clean_xi(self, indices, team, other_players):
        team["first_xi"] = 0
        team.loc[indices, "first_xi"] = 1
        team = team.sort_values("first_xi", ascending=False)
        team = team.drop("index", axis=1).reset_index(drop=True)

        team = pd.concat([team, other_players])
        team["season"] = self.season
        team["picked_time"] = dt.datetime.now()

        for col in ["is_home1", "is_home2", "is_home3"]:
            if col in team.columns:
                team[col] = team[col].replace({0: np.nan, float(0): np.nan})
        return team

    def pick_xi(self):
        other_players = self.first_xv.loc[self.first_xv["picked"] != 1]
        team = self.first_xv.loc[self.first_xv["picked"] == 1]

        players = [LpVariable("player_" + str(i), cat="Binary") for i in team.index]
        prob = LpProblem("First team choices", LpMaximize)

        prob += lpSum(
            players[i] * team.points_weighted.to_list()[i] for i in range(len(team))
        )
        prob += sum(players) == 11
        prob = self._add_position_constraints(prob, players, team, "XI")
        prob.solve()

        indices = self._player_indices(players)
        team = self._clean_xi(indices, team, other_players)
        self.first_xi = team
        return team

    # existing picking code
    # def update_xi(self, max_changes):
    #     # how to give it the starting point of the previous team and ask it to make a single change?
    #     # prob = self._initialise_prob()
    #     prob = LpProblem("FPL Player Choices", LpMaximize)

    #     # Add objective function
    #     # # why am i not using points_weighted here...?
    #     # max_var = self.max_var if self.max_var == "value_fixture" else "total_points"
    #     max_var = "points_weighted"  # some error to do with this
    #     prob += lpSum(
    #         (self.players[i] + self.captains[i]) * self.player_df[max_var][i]
    #         for i in range(len(self.player_df))
    #     )
    #     prob = self._add_xv_constraints(prob)
    #     prob = self._add_changes_constraint(prob, max_changes)
    #     prob.solve()

    #     indices = self._player_indices(self.players)
    #     captain_index = self._captain_index(self.captains)

    #     team = self._clean_xv(indices, captain_index)
    #     self.first_xv = team
    #     return self.pick_xi()

    # def update_xi(self, max_changes):
    #     # how to give it the starting point of the previous team and ask it to make a single change?
    #     players = [
    #         LpVariable("player_" + str(i), cat="Binary") for i in self.player_df.index
    #     ]
    #     captain_decisions = [
    #         LpVariable("captain_" + str(i), cat="Binary") for i in self.player_df.index
    #     ]

    #     # this doesn't work...
    #     changes = [
    #         LpVariable("change_" + str(i), cat="Binary") for i in self.player_df.index
    #     ]

    #     prob = LpProblem("FPL Player Choices", LpMaximize)

    #     prob += lpSum(
    #         (players[i] + captain_decisions[i]) * self.points_weighted[i]
    #         for i in range(len(self.player_df))
    #     )
    #     prob += sum(players) == 15
    #     prob += (
    #         lpSum(
    #             players[i] * self.player_df.value[self.player_df.index[i]]
    #             for i in range(len(self.player_df))
    #         )
    #         <= 1200
    #     )

    #     prob += sum(captain_decisions) == 1

    #     for pos in ["GK", "DEF", "MID", "FWD"]:
    #         prob += (
    #             lpSum(
    #                 players[i]
    #                 for i in range(len(self.player_df))
    #                 if self.positions[i] == pos
    #             )
    #             <= self.POS_CONSTRAINTS["XV"][pos][0]
    #         )

    #     for club in self.teams:
    #         # Club Limit
    #         prob += (
    #             lpSum(
    #                 players[i]
    #                 for i in range(len(self.player_df))
    #                 if self.teams[i] == club
    #             )
    #             <= 3
    #         )

    #     for i in range(len(self.player_df)):
    #         prob += (players[i] - captain_decisions[i]) >= 0

    #     # add constraint for the changes -> number of original players must be 15 - max_changes
    #     prob += (
    #         lpSum(
    #             changes[i]
    #             for i in range(len(self.player_df))
    #             if self.player_df["initial_team"][i]
    #         )
    #         >= 15 - max_changes
    #     )
    #     prob.solve()

    #     players = [player for player in players if player.varValue != 0]
    #     captain = [player for player in captain_decisions if player.varValue != 0]
    #     captain_index = int(captain[0].name.split("_")[1])

    #     indices = [int(player.name.split("_")[1]) for player in players]

    #     team_2 = self.player_df.copy(deep=True)
    #     team_2.loc[indices, "picked"] = 1
    #     team_2.loc[team_2["picked"] != 1, "picked"] = 0
    #     team_2["captain"] = 0
    #     team_2.loc[captain_index, "captain"] = 1

    #     team_2 = team_2.drop("index", axis=1).reset_index()
    #     self.first_xv = team_2
    #     return self.pick_xi()


if __name__ == "__main__":
    import sys

    sys.path.append("/Users/toby/Dev/lionel/src")
    import requests

    # from team.team import Team
    # from run import run

    from scrape.combine import BetFPLCombiner
    from scrape.players.process import FPLProcessor
    from scrape.bet.scrape import FutureBetScraper

    fproc = FPLProcessor(24, 28)
    bs = FutureBetScraper()
    bs.run_scrape()
    df_odds = bs.to_df()

    bfc = BetFPLCombiner(24, df_odds, fproc.player_stats)
    bfc.prepare_next_gw()
    df_final = bfc.df_next_game

    selector = DumbOptimiser(df_final, 24)
    # selector._pick_xv()
    # team1 = selector.first_xv
    selector.pick_xi()
    team2 = selector.first_xi

    assert len(team2[team2.picked == 1]) == 15
    assert len(team2[team2.first_xi == 1]) == 11

    # print(team2)
    # test team update
    # team_id = "5595564"
    # GW = 26
    # url2 = f"https://fantasy.premierleague.com/api/entry/{team_id}/event/{GW}/picks/"

    # r = requests.get(url2)
    # picks = r.json()["picks"]
    # df = pd.DataFrame.from_dict(picks)
    # elements = get_existing_player_elements(team_id, GW)

    # team = run(24, 28)  # what?
    # team2 = Team(24, 28, team.df_next_game, initial_xi=elements)

    # # selector = team2.selector
    # team2.pick_xi()
