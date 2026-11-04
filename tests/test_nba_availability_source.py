import copy
import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from nba_availability_source import apply_saved


class SavedAvailabilityTests(unittest.TestCase):
    def test_saved_report_preserves_original_observation(self):
        now = datetime(2026, 11, 4, 1, tzinfo=timezone.utc)
        game = {"id": "g", "date": now.isoformat(), "away": {"id": "1"}, "home": {"id": "2"}}
        report = {"state": "reported", "game_date": "2026-11-03", "checked_at": now.isoformat(), "report_as_of": now.isoformat(), "players": []}
        doc = {"collected_at": now.isoformat(), "games": {"g": {"date": game["date"], "away": {"team_id": "1", "availability": report}}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "availability.json"
            path.write_text(json.dumps(doc))
            games = [copy.deepcopy(game)]
            apply_saved(games, now, path)
            self.assertEqual(games[0]["away"]["availability"], report)
            self.assertEqual(games[0]["home"]["availability"]["state"], "unavailable")
            doc["collected_at"] = (now - timedelta(hours=19)).isoformat()
            path.write_text(json.dumps(doc))
            games = [copy.deepcopy(game)]
            apply_saved(games, now, path)
            self.assertEqual(games[0]["away"]["availability"]["state"], "unavailable")

    def test_missing_source_keeps_future_games_pending(self):
        now = datetime(2026, 11, 4, 1, tzinfo=timezone.utc)
        games = [{"id": "g", "date": (now + timedelta(days=1)).isoformat(), "away": {"id": "1"}, "home": {"id": "2"}}]
        with tempfile.TemporaryDirectory() as directory:
            apply_saved(games, now, Path(directory) / "missing.json")
        self.assertEqual(games[0]["away"]["availability"]["state"], "pending")
