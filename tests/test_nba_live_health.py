import unittest
from datetime import datetime, timezone, timedelta
from verify_nba_pipeline import fresh, matching_counts


class LiveHealthTests(unittest.TestCase):
    def test_recent_observation_and_small_clock_skew(self):
        now = datetime.now(timezone.utc)
        fresh((now - timedelta(hours=2)).isoformat(), now)
        fresh((now + timedelta(minutes=2)).isoformat(), now)

    def test_stale_and_future_observations_are_rejected(self):
        now = datetime.now(timezone.utc)
        for value in (now - timedelta(hours=31), now + timedelta(minutes=10)):
            with self.assertRaises(ValueError):
                fresh(value.isoformat(), now)

    def test_matching_verified_publications(self):
        matching_counts(107, 107, 107, 107)

    def test_lagging_leaders_or_team_outputs_fail(self):
        for values in ((107, 107, 107, 106), (107, 106, 107, 107), (107, 107, 106, 107)):
            with self.assertRaises(ValueError):
                matching_counts(*values)
