import unittest
from datetime import datetime, timezone, timedelta
from verify_mlb_pipeline import verify_source


class MLBHealthTests(unittest.TestCase):
    def test_complete_current_source_passes(self):
        now=datetime.now(timezone.utc)
        verify_source({"season":2026,"phase":3,"collected_at":now.isoformat(),"teams":{str(i):{} for i in range(30)}},2026,3,now,True)

    def test_wrong_context_and_missing_teams_fail(self):
        now=datetime.now(timezone.utc)
        for year,phase in ((2025,3),(2026,2)):
            with self.assertRaises(ValueError):
                verify_source({"season":year,"phase":phase,"collected_at":now.isoformat()},2026,3,now)
        with self.assertRaises(ValueError):
            verify_source({"season":2026,"phase":3,"collected_at":now.isoformat(),"teams":{}},2026,3,now,True)

    def test_stale_and_future_observations_fail(self):
        now=datetime.now(timezone.utc)
        for delta in (timedelta(hours=31),-timedelta(minutes=10)):
            with self.assertRaises(ValueError):
                verify_source({"season":2026,"phase":3,"collected_at":(now-delta).isoformat()},2026,3,now)
