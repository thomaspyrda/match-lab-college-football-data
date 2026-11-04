import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from mlb_player_source import load_player_stats


class PlayerSourceTests(unittest.TestCase):
    def test_offseason_without_upcoming_teams_needs_no_player_source(self):
        self.assertEqual(load_player_stats(Path("missing"), 2026, 3, [], datetime.now(timezone.utc)), {})

    def test_complete_saved_statistics_are_preserved(self):
        now = datetime.now(timezone.utc)
        doc = {"season": 2026, "phase": 3, "collected_at": now.isoformat(), "teams": {str(i): {"player": {"era": 2.5, "ip": "4.2"}} for i in range(30)}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "players.json"
            path.write_text(json.dumps(doc))
            self.assertEqual(load_player_stats(path, 2026, 3, ["1"], now), doc["teams"])
            for year, phase, ids in ((2025, 3, ["1"]), (2026, 2, ["1"]), (2026, 3, ["unknown"])):
                with self.assertRaises(ValueError):
                    load_player_stats(path, year, phase, ids, now)
            doc["collected_at"] = (now-timedelta(hours=31)).isoformat()
            path.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):
                load_player_stats(path, 2026, 3, ["1"], now)
