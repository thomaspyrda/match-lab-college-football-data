import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("yardage", ROOT / "scripts/cfb_dashboard_yardage.py")
yardage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(yardage)


class YardageTests(unittest.TestCase):
    def snapshot(self):
        values = dict(games=2, netPassingYards=400, passCompletions=40,
                      rushingYards=180, rushingAttempts=60, netPassingYardsOpponent=200,
                      passCompletionsOpponent=25, rushingYardsOpponent=120, rushingAttemptsOpponent=50)
        basic = [dict(team=team, season=2026, statName=k, statValue=v)
                 for team in ("A", "B", "FCS") for k, v in values.items()]
        advanced = [dict(team=team, season=2026, offense=dict(lineYards=off), defense=dict(lineYards=defense))
                    for team, off, defense in (("A", 3.2, 2.4), ("B", 3.2, 2.8), ("FCS", 8, 1))]
        return dict(season=2026, collected_at="2026-11-05T00:00:00+00:00", through_week=10,
                    payload=dict(basic=basic, advanced=advanced, dashboard=dict(teams={"A": {"offensive_ppa_rank": 1}, "B": {"offensive_ppa_rank": 2}, "FCS": {"offensive_ppa_rank": None}})))

    def test_denominators_ties_and_defensive_rank_direction(self):
        board = yardage.board(self.snapshot())
        self.assertEqual(board["a"]["offense"]["pass_yards_per_game"], 200)
        self.assertEqual(board["a"]["offense"]["yards_per_completion"], 10)
        self.assertEqual(board["a"]["offense"]["rush_yards_per_game"], 90)
        self.assertEqual(board["a"]["offense"]["yards_per_carry"], 3)
        self.assertEqual(board["a"]["defense"]["yards_per_carry"], 2.4)
        self.assertEqual(board["a"]["offense"]["line_yards_rank"], 1)
        self.assertEqual(board["b"]["offense"]["line_yards_rank"], 1)
        self.assertEqual(board["a"]["defense"]["line_yards_rank"], 1)
        self.assertEqual(board["b"]["defense"]["line_yards_rank"], 2)
        self.assertIsNone(board["fcs"]["offense"]["line_yards_rank"])

    def test_missing_denominator_and_bad_values_are_unavailable(self):
        snapshot = self.snapshot()
        for row in snapshot["payload"]["basic"]:
            if row["team"] == "A" and row["statName"] in {"games", "passCompletions"}:
                row["statValue"] = 0
        board = yardage.board(snapshot)
        self.assertIsNone(board["a"]["offense"]["pass_yards_per_game"])
        self.assertIsNone(board["a"]["offense"]["yards_per_completion_rank"])
        self.assertIsNone(yardage.number("NaN"))

    def test_enrichment_preserves_existing_results_and_is_idempotent(self):
        payload = dict(games=[dict(season=2026, away=dict(name="A"), home=dict(name="B"),
                                  matchup_metrics=[dict(label="EPA / Play", away_offense=0.15)],
                                  market=dict(spread=3), players=[dict(name="Player")])])
        original = copy.deepcopy(payload)
        enriched = yardage.enrich(payload, self.snapshot())
        self.assertEqual(enriched["games"][0]["matchup_metrics"][0], original["games"][0]["matchup_metrics"][0])
        self.assertEqual(enriched["games"][0]["market"], original["games"][0]["market"])
        self.assertEqual(enriched["games"][0]["players"], original["games"][0]["players"])
        again = yardage.enrich(copy.deepcopy(enriched), self.snapshot())
        self.assertEqual(enriched, again)
        self.assertEqual(len(enriched["games"][0]["matchup_metrics"]), 6)

    def test_current_snapshot_has_usable_yardage_and_preserves_existing_metrics(self):
        path = ROOT / "data/cfb/pipeline/metrics.json"
        dashboard = ROOT / "cfb-dashboard-preview/data/dashboard.json"
        if not path.exists() or not dashboard.exists():
            self.skipTest("Live snapshots are not available")
        snapshot, payload = json.loads(path.read_text()), json.loads(dashboard.read_text())
        old = copy.deepcopy(payload)
        enriched = yardage.enrich(payload, snapshot)
        labels = {m[0] for m in yardage.METRICS}
        populated = 0
        for before, after in zip(old["games"], enriched["games"]):
            self.assertEqual([m for m in before["matchup_metrics"] if m["label"] not in labels],
                             [m for m in after["matchup_metrics"] if m["label"] not in labels])
            for metric in after["matchup_metrics"]:
                if metric["label"] in labels:
                    populated += metric.get("away_offense") is not None
                    for side in ("away", "home"):
                        for phase in ("offense", "defense"):
                            value = metric.get(side + "_" + phase)
                            rank = metric.get(side + "_" + phase + "_rank")
                            if value is None:
                                self.assertIsNone(rank)
                            elif rank is not None:
                                self.assertTrue(1 <= rank <= 150)
        self.assertGreater(populated, 0)
