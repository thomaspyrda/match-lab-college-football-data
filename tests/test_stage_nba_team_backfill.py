import unittest
from stage_nba_team_backfill import build_manifest

def registry():
    teams=[{"sport":"nba","espn_id":str(i),"slug":f"team-{i}"} for i in range(1,31)]
    return {"teams":teams}

def game(market=None):
    return {"id":"999","season":2027,"phase":2,"home":"1","date":"2026-10-20T23:00:00+00:00",
      "observed_complete_at":"2026-10-21T04:00:00+00:00",
      "teams":{"1":{"points":110},"2":{"points":100}},"players":{"1":[],"2":[]},"pregame_market":market}

class AdapterTest(unittest.TestCase):
    def test_without_market_does_not_guess(self):
        r=build_manifest(registry(),{"games":[game()]})
        self.assertEqual(r["coverage"]["without_valid_pregame_market"],1)
        self.assertIsNone(r["teams"]["team-1"][0]["ats_result"])
        self.assertEqual(len(r["teams"]["team-2"]),1)
    def test_valid_pregame_market(self):
        market={"home_spread":-9.5,"total":208.5,"source":"approved-example","observed_at":"2026-10-20T22:00:00+00:00"}
        r=build_manifest(registry(),{"games":[game(market)]})
        self.assertEqual(r["teams"]["team-1"][0]["ats_result"],"W")
        self.assertEqual(r["teams"]["team-2"][0]["ats_result"],"L")
        self.assertEqual(r["teams"]["team-1"][0]["ou_result"],"Over")
    def test_postgame_market_rejected(self):
        market={"home_spread":-9.5,"total":208.5,"source":"example","observed_at":"2026-10-21T00:00:00+00:00"}
        r=build_manifest(registry(),{"games":[game(market)]})
        self.assertIsNone(r["teams"]["team-1"][0]["total"])

if __name__=="__main__":unittest.main()
