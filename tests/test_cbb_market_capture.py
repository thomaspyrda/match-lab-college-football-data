import unittest
from datetime import datetime, timezone
from sync_cbb_market_archives import capture_event

class MarketSafetyTests(unittest.TestCase):
    def event(self):
        return {
            "id": "123", "date": "2026-11-01T19:00:00Z",
            "season": {"year": 2027}, "status": {"type": {"completed": False}},
            "competitions": [{"competitors": [
                {"homeAway": "home", "team": {"id": "87"}},
                {"homeAway": "away", "team": {"id": "222"}}
            ], "odds": [{"spread": 4.5, "overUnder": 142.5,
                         "homeTeamOdds": {"favorite": True},
                         "awayTeamOdds": {"favorite": False},
                         "provider": {"name": "Recorded Provider"}}]}]
        }

    def test_pretip_quote_is_accepted(self):
        row = capture_event(self.event(), datetime(2026,11,1,18,0,tzinfo=timezone.utc))
        self.assertEqual(row["home_spread"], -4.5)
        self.assertEqual(row["total"], 142.5)

    def test_posttip_quote_rejected(self):
        self.assertIsNone(capture_event(self.event(),datetime(2026,11,1,19,1,tzinfo=timezone.utc)))

    def test_completed_event_rejected(self):
        event = self.event()
        event["status"]["type"]["completed"] = True
        self.assertIsNone(capture_event(event,datetime(2026,11,1,18,0,tzinfo=timezone.utc)))

    def test_unverified_spread_side_not_assumed(self):
        event = self.event()
        del event["competitions"][0]["odds"][0]["homeTeamOdds"]
        del event["competitions"][0]["odds"][0]["awayTeamOdds"]
        row = capture_event(event,datetime(2026,11,1,18,0,tzinfo=timezone.utc))
        self.assertIsNone(row["home_spread"])
        self.assertEqual(row["total"],142.5)

if __name__ == "__main__":
    unittest.main()
