import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from nba_roster_source import collect, load_rosters


class RosterSourceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.row = {"team_id": "1", "observed_at": "2026-10-31T12:00:00+00:00", "source": "verified", "players": [{"id": "p", "name": "Player"}]}

    def test_collection_keeps_existing_roster_contract(self):
        result = collect(["1"], 2027, lambda tid: self.row, {}, self.now)
        self.assertEqual(result["teams"]["1"], self.row)

    def test_failed_request_retains_original_timestamp(self):
        def fail(tid):
            raise OSError("unavailable")
        result = collect(["1"], 2027, fail, {"1": self.row}, self.now)
        self.assertEqual(result["teams"]["1"], self.row)
        self.assertEqual(result["retained_teams"], ["1"])

    def test_no_verified_fallback_blocks_initial_publication(self):
        with self.assertRaisesRegex(ValueError, "No verified"):
            collect(["1"], 2027, lambda tid: {}, {}, self.now)

    def test_saved_roster_validation_rejects_wrong_season_and_team(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rosters.json"
            path.write_text(json.dumps({"season": 2027, "teams": {"1": self.row}}))
            self.assertEqual(load_rosters(path, 2027, ["1"]), {"1": self.row})
            with self.assertRaises(ValueError):
                load_rosters(path, 2026, ["1"])
            with self.assertRaises(ValueError):
                load_rosters(path, 2027, ["2"])
