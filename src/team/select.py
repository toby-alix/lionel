import numpy as np
import datetime as dt
import pandas as pd
from pulp import LpVariable, LpProblem, lpSum, LpMaximize
from abc import ABCMeta, abstractmethod


class Optimiser(metaclass=ABCMeta):

    POS_CONSTRAINTS = {
        "XV": {
            "DEF": 5,
            "FWD": 3,
            "MID": 5,
            "GK": 2,
        },
        "XI": {
            "DEF": [3, 5],
            "FWD": [1, 3],
            "MID": [2, 5],
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

    @property
    def first_xv(self):
        if self._first_xv.empty:
            self._first_xv = self._pick_xv()
        return self._first_xv

    @first_xv.setter
    def first_xv(self, val):
        self._first_xv = val

    def _pick_xv(self):
        players = [
            LpVariable("player_" + str(i), cat="Binary") for i in self.player_df.index
        ]
        captain_decisions = [
            LpVariable("captain_" + str(i), cat="Binary") for i in self.player_df.index
        ]
        prob = LpProblem("FPL Player Choices", LpMaximize)

        # Objective - I want to maximise next fixture with total points - how do I combine them? Scale them both and then take the mean of the two?
        if self.max_var == "value_fixture":
            prob += lpSum(
                (players[i] + captain_decisions[i]) * self.points_weighted[i]
                for i in range(len(self.player_df))
            )
        else:
            prob += lpSum(
                (players[i] + captain_decisions[i]) * self.total_points[i]
                for i in range(len(self.player_df))
            )

        # Constraints
        prob += sum(players) == 15
        prob += (
            lpSum(
                players[i] * self.player_df.value[self.player_df.index[i]]
                for i in range(len(self.player_df))
            )
            <= self.budget
        )
        prob += sum(captain_decisions) == 1

        for pos in ["GK", "DEF", "MID", "FWD"]:
            prob += (
                lpSum(
                    players[i]
                    for i in range(len(self.player_df))
                    if self.positions[i] == pos
                )
                <= self.POS_CONSTRAINTS["XV"][pos]
            )

        for club in self.teams:
            prob += (
                lpSum(
                    players[i]
                    for i in range(len(self.player_df))
                    if self.teams[i] == club
                )
                <= 3
            )  # Club Limit

        for i in range(len(self.player_df)):
            prob += (players[i] - captain_decisions[i]) >= 0

        prob.solve()

        players = [player for player in players if player.varValue != 0]
        captain = [player for player in captain_decisions if player.varValue != 0]
        captain_index = int(captain[0].name.split("_")[1])

        indices = [int(player.name.split("_")[1]) for player in players]

        team_2 = self.player_df.copy(deep=True)
        team_2.loc[indices, "picked"] = 1
        team_2.loc[team_2["picked"] != 1, "picked"] = 0
        team_2["captain"] = 0
        team_2.loc[captain_index, "captain"] = 1

        team_2 = team_2.drop("index", axis=1).reset_index()
        return team_2

    # maybe make this
    def pick_xi(self):
        other_players = self.first_xv.loc[self.first_xv["picked"] != 1]
        team = self.first_xv.loc[self.first_xv["picked"] == 1]

        players = [LpVariable("player_" + str(i), cat="Binary") for i in team.index]

        prob = LpProblem("First team choices", LpMaximize)

        prob += lpSum(players[i] * self.points_weighted[i] for i in range(len(team)))
        prob += sum(players) == 11

        for pos in ["GK", "DEF", "MID", "FWD"]:
            prob += (
                lpSum(players[i] for i in range(len(team)) if self.positions[i] == pos)
                >= self.POS_CONSTRAINTS["XI"][pos][0]
            )
            prob += (
                lpSum(players[i] for i in range(len(team)) if self.positions[i] == pos)
                <= self.POS_CONSTRAINTS["XI"][pos][1]
            )

        prob.solve()

        players = [player for player in players if player.varValue != 0]
        indices = [int(player.name.split("_")[1]) for player in players]

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

    # existing picking code
    def update_xi(self, max_changes):
        # how to give it the starting point of the previous team and ask it to make a single change?
        players = [
            LpVariable("player_" + str(i), cat="Binary") for i in self.player_df.index
        ]
        captain_decisions = [
            LpVariable("captain_" + str(i), cat="Binary") for i in self.player_df.index
        ]

        changes = [
            LpVariable("change_" + str(i), cat="Binary") for i in self.player_df.index
        ]

        prob = LpProblem("FPL Player Choices", LpMaximize)

        prob += lpSum(
            (players[i] + captain_decisions[i]) * self.points_weighted[i]
            for i in range(len(self.player_df))
        )
        prob += sum(players) == 15
        prob += (
            lpSum(
                players[i] * self.player_df.value[self.player_df.index[i]]
                for i in range(len(self.player_df))
            )
            <= 1010
        )

        prob += sum(captain_decisions) == 1

        for pos in ["GK", "DEF", "MID", "FWD"]:
            prob += (
                lpSum(
                    players[i]
                    for i in range(len(self.player_df))
                    if self.positions[i] == pos
                )
                <= self.POS_CONSTRAINTS["XV"][pos]
            )

        for club in self.teams:
            prob += (
                lpSum(
                    players[i]
                    for i in range(len(self.player_df))
                    if self.teams[i] == club
                )
                <= 3
            )  # Club Limit

        for i in range(len(self.player_df)):
            prob += (players[i] - captain_decisions[i]) >= 0

        # add constraint for the changes -> number of original players must be 15 - max_changes
        prob += (
            lpSum(
                changes[i]
                for i in range(len(self.player_df))
                if self.player_df["initial_team"][i]
            )
        ) >= 15 - max_changes
        prob.solve()

        players = [player for player in players if player.varValue != 0]
        captain = [player for player in captain_decisions if player.varValue != 0]
        captain_index = int(captain[0].name.split("_")[1])

        indices = [int(player.name.split("_")[1]) for player in players]

        team_2 = self.player_df.copy(deep=True)
        team_2.loc[indices, "picked"] = 1
        team_2.loc[team_2["picked"] != 1, "picked"] = 0
        team_2["captain"] = 0
        team_2.loc[captain_index, "captain"] = 1

        team_2 = team_2.drop("index", axis=1).reset_index()
        self.first_xv = team_2
        return self.pick_xi()

        # add constraint for max changes - how to do this?
        # could add a column
