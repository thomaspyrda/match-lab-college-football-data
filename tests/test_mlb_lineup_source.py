import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from mlb_lineup_source import signature, load_context


class LineupSourceTests(unittest.TestCase):
    def test_saved_context_requires_exact_event_and_fresh_observation(self):
        now = datetime.now(timezone.utc)
        event = {"id": "g", "date": now.isoformat(), "competitions": [{"competitors": [{"team": {"id": "1"}}, {"team": {"id": "2"}}]}]}
        doc = {"season": 2026, "phase": 3, "collected_at": now.isoformat(), "events": {"g": signature(event)}, "lineups": {"g": {"1": [{"name": "Player"}]}}, "recent_lineups": {}, "starters": []}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lineups.json"
            path.write_text(json.dumps(doc))
            self.assertEqual(load_context(path, 2026, 3, [event], now)[0], doc["lineups"])
            self.assertEqual(load_context(path, 2025, 3, [event], now), ({}, {}, {}))
            self.assertEqual(load_context(path, 2026, 3, [event], now+timedelta(hours=7)), ({}, {}, {}))
            event["date"] = (now+timedelta(days=1)).isoformat()
            self.assertEqual(load_context(path, 2026, 3, [event], now)[0], {})

    def test_missing_context_never_invents_a_lineup(self):
        self.assertEqual(load_context(Path("missing.json"), 2026, 3, [], datetime.now(timezone.utc)), ({}, {}, {}))
