import json
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from mlb_metric_source import load_profiles


class MetricSourceTests(unittest.TestCase):
    def test_profiles_are_preserved_and_wrong_context_is_rejected(self):
        now = datetime.now(timezone.utc)
        doc = {"season": 2026, "phase": 3, "collected_at": now.isoformat(), "teams": {"1": {"games": 2, "metrics": {"era": 3.5}}}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            path.write_text(json.dumps(doc))
            self.assertEqual(load_profiles(path, 2026, 3, ["1"], now), doc["teams"])
            for year, phase, ids in ((2025, 3, ["1"]), (2026, 2, ["1"]), (2026, 3, ["1", "2"])):
                with self.assertRaises(ValueError):
                    load_profiles(path, year, phase, ids, now)

    def test_stale_and_future_profiles_are_rejected(self):
        now = datetime.now(timezone.utc)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.json"
            for age in (timedelta(hours=31), -timedelta(minutes=10)):
                path.write_text(json.dumps({"season": 2026, "phase": 3, "collected_at": (now-age).isoformat(), "teams": {"1": {}}}))
                with self.assertRaises(ValueError):
                    load_profiles(path, 2026, 3, ["1"], now)
