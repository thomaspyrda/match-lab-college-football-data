"""Verify one sport cannot prevent another sport's pregame refresh."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import refresh_afternoon_pregame as pregame


class PregameIsolationTests(unittest.TestCase):
    def test_selected_sport_is_the_only_refresh(self):
        with patch.object(pregame, "refresh") as refresh:
            pregame.main(["--sport", "cbb"])
        refresh.assert_called_once_with("cbb", *pregame.SPORTS["cbb"])

    def test_failure_does_not_stop_other_sports_and_is_reported(self):
        visited = []

        def refresh(sport, *_):
            visited.append(sport)
            if sport == "nba":
                raise RuntimeError("source unavailable")

        with patch.object(pregame, "refresh", side_effect=refresh):
            with self.assertRaisesRegex(SystemExit, "nba"):
                pregame.main([])
        self.assertEqual(visited, list(pregame.SPORTS))

    def test_selected_failure_does_not_refresh_another_sport(self):
        with patch.object(pregame, "refresh", side_effect=RuntimeError("offline")) as refresh:
            with self.assertRaisesRegex(SystemExit, "mlb"):
                pregame.main(["--sport", "mlb"])
        refresh.assert_called_once_with("mlb", *pregame.SPORTS["mlb"])

    def test_market_refresh_preserves_final_games_statistics_and_rankings(self):
        final = {"id": "final", "status": "Final", "market": {"total": 150},
                 "points": 80, "opponent_points": 70}
        upcoming = {"id": "upcoming", "status": "Scheduled", "stats": {"ppg": 75},
                    "rank": 12, "market": {"total": 140}}
        snapshot = {"games": [final, upcoming], "teams": {"a": {"ppg": 75}},
                    "rankings": {"a": 12}, "updated_at": "existing-stats-timestamp"}
        events = [
            {"id": "final", "status": {"type": {"completed": True}},
             "competitions": [{"odds": [{"overUnder": 999}]}]},
            {"id": "upcoming", "status": {"type": {"completed": False,
                                                    "description": "Scheduled"}},
             "competitions": [{"odds": [{"details": "A -2.5", "overUnder": 145,
                                         "provider": {"name": "Observed"}}]}]},
        ]
        before = copy.deepcopy(snapshot)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            dest = root / "dashboard.json"
            dest.write_text(json.dumps(snapshot))
            with patch.object(pregame, "ROOT", root), patch.object(
                    pregame, "request", return_value={"events": events}):
                pregame.refresh("cbb", "basketball/mens-college-basketball", "dashboard.json")
            after = json.loads(dest.read_text())
        self.assertEqual(after["games"][0], before["games"][0])
        self.assertEqual(after["teams"], before["teams"])
        self.assertEqual(after["rankings"], before["rankings"])
        self.assertEqual(after["updated_at"], before["updated_at"])
        self.assertEqual(after["games"][1]["stats"], upcoming["stats"])
        self.assertEqual(after["games"][1]["rank"], 12)
        self.assertEqual(after["games"][1]["market"]["total"], 145)


if __name__ == "__main__":
    unittest.main()
