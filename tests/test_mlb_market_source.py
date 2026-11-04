import json
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timezone, timedelta
from mlb_market_source import load_markets


class MarketSourceTests(unittest.TestCase):
    def test_saved_quotes_and_records_are_preserved(self):
        now = datetime.now(timezone.utc)
        doc = {"season": 2026, "phase": 3, "collected_at": now.isoformat(), "quotes": {"g": {"overUnder": 8.5}}, "teams": {str(i): {"locations": {}, "ats": {"lined_games": 0}} for i in range(30)}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "markets.json"
            path.write_text(json.dumps(doc))
            self.assertEqual(load_markets(path, 2026, 3, now), (doc["quotes"], doc["teams"]))
            for year, phase, when in ((2025, 3, now), (2026, 2, now), (2026, 3, now+timedelta(hours=31))):
                self.assertEqual(load_markets(path, year, phase, when), ({}, {}))

    def test_missing_quotes_do_not_create_market_records(self):
        self.assertEqual(load_markets(Path("missing"), 2026, 3, datetime.now(timezone.utc)), ({}, {}))
