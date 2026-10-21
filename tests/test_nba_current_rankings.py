import copy
import json
import unittest
from pathlib import Path

from build_nba_team_rankings import TEAM_INFO, METRIC_LABELS, rate_teams
from nba_current_rankings import build_current_rows, game_minutes

REGISTRY = json.loads((Path(__file__).resolve().parents[1] / "data/sports/team-registry.json").read_text())


def fixture():
    a = dict(points=110, fgm=40, fga=90, tpm=10, tpa=30, ftm=20, fta=25,
             oreb=10, dreb=30, reb=40, ast=25, tov=12, stl=7, blk=5)
    b = dict(points=100, fgm=35, fga=85, tpm=10, tpa=30, ftm=20, fta=25,
             oreb=8, dreb=28, reb=36, ast=20, tov=14, stl=5, blk=4)
    return dict(id="one", season=2027, phase=2, date="2026-10-21T01:00Z",
                observed_complete_at="2026-10-21T05:00:00+00:00", home="2", periods=4,
                teams={"2": a, "8": b}, neutral=False)


def build(games):
    rows, coverage = build_current_rows({"games": games}, REGISTRY, TEAM_INFO, 2027, METRIC_LABELS)
    rate_teams(rows)
    return {r["slug"]: r for r in rows}, coverage


class CurrentRankingsTests(unittest.TestCase):
    def test_regular_season_isolation_and_unplayed_teams(self):
        g = fixture()
        ignored = [dict(g, id="pre", phase=1), dict(g, id="post", phase=3),
                   dict(g, id="old", season=2026)]
        teams, coverage = build([g, *ignored])
        self.assertEqual(len(teams), 30)
        self.assertEqual(coverage["completed_games"], 1)
        self.assertEqual(coverage["ranked_teams"], 2)
        self.assertEqual(coverage["through_date"], "2026-10-20")
        own = teams["boston-celtics"]
        self.assertEqual(own["record"], "1–0")
        self.assertEqual(own["ranks"]["overall"], 1)
        self.assertAlmostEqual(own["metrics"]["ortg"], 11000 / 102.5, places=3)
        self.assertAlmostEqual(own["metrics"]["defensive_rebound_rate"], 3000 / 38, places=3)
        self.assertIsNone(own["metrics"]["opp_rim_fg_pct"])
        for row in teams.values():
            if not row["games_played"]:
                self.assertEqual(row["record"], "0–0")
                self.assertTrue(all(v is None for v in row["ranks"].values()))
                self.assertIsNone(row["metrics"]["ppg"])

    def test_percentages_use_totals_and_home_away_splits(self):
        g = fixture()
        second = copy.deepcopy(g)
        second.update(id="two", home="8", date="2026-10-22T00:00Z")
        second["teams"]["2"].update(points=70, fgm=20, fga=50)
        teams, _ = build([g, second])
        row = teams["boston-celtics"]
        self.assertEqual(row["record"], "1–1")
        self.assertAlmostEqual(row["metrics"]["fg_pct"], 6000 / 140, places=3)
        self.assertEqual(row["metrics"]["ppg_home"], 110)
        self.assertEqual(row["metrics"]["ppg_away"], 70)

    def test_overtime_pace(self):
        g = fixture()
        g["periods"] = 5
        teams, _ = build([g])
        self.assertAlmostEqual(teams["boston-celtics"]["metrics"]["pace"], 102.5 * 48 / 53, places=3)
        del g["periods"]
        g["players"] = {tid: [{"minutes": 265}] for tid in g["teams"]}
        self.assertEqual(game_minutes(g), 53)

    def test_empty_season_is_not_ranked_or_filled_with_zero_stats(self):
        teams, coverage = build([])
        self.assertEqual(coverage["ranked_teams"], 0)
        self.assertTrue(all(r["ranks"]["overall"] is None for r in teams.values()))
        self.assertTrue(all(r["ratings"]["overall_sd"] is None for r in teams.values()))

    def test_duplicate_games_not_double_counted(self):
        g = fixture()
        teams, coverage = build([g, copy.deepcopy(g)])
        self.assertEqual(coverage["completed_games"], 1)
        self.assertEqual(sum(r["games_played"] for r in teams.values()), 2)
        conflicting = dict(g, date="2026-10-22T00:00Z")
        with self.assertRaises(ValueError):
            build([g, conflicting])

    def test_bad_boxscore_stops_publication(self):
        g = fixture()
        g["teams"]["2"]["fga"] = None
        with self.assertRaises(ValueError):
            build([g])
        g = fixture()
        g["teams"]["2"]["points"] = 111
        with self.assertRaises(ValueError):
            build([g])


if __name__ == "__main__":
    unittest.main()
