import unittest
from daily_backfill_core import GameObservation, market_result, accept_pregame_market

class DailyBackfillTest(unittest.TestCase):
    def test_final_game(self):
        GameObservation("nba","123","2026-10-20T18:00:00+00:00","2026-10-20","bos","nyk","final",110,100).validate()
    def test_no_synthetic_result(self):
        with self.assertRaises(ValueError):
            GameObservation("cbb","g","2026-11-04T12:00:00+00:00","2026-11-04","a","b","final").validate()
    def test_market_settlement(self):
        self.assertEqual(market_result("nba",110,100,home_spread=-9.5,total=210)["home_ats_or_runline"],"W")
        self.assertEqual(market_result("nba",110,100,home_spread=-9.5,total=210)["ou"],"Push")
        self.assertEqual(market_result("mlb",5,4,home_spread=-1.5,total=8.5)["home_ats_or_runline"],"L")
        self.assertIsNone(market_result("cbb",80,78)["ou"])
    def test_pregame_market_only(self):
        t="2026-10-20T23:00:00+00:00"
        self.assertTrue(accept_pregame_market(t,"2026-10-20T22:00:00+00:00",{"source":"licensed","total":224.5}))
        self.assertFalse(accept_pregame_market(t,t,{"source":"licensed","total":224.5}))
        self.assertFalse(accept_pregame_market(t,"2026-10-20T22:00:00+00:00",{"total":224.5}))

if __name__ == "__main__":
    unittest.main()
