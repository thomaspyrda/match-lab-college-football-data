import unittest
from combine_mlb_historical_staging import combine

def stage(year,gameid):
    return {"status":"HISTORICAL_STAGING_ONLY","season":year,
      "games":{gameid:{"game_id":gameid,"season":year,"phase":"regular"}}}
def audit(year,matching=30):
    return {"year":year,"teams_checked":30,"teams_matching":matching,
      "teams_mismatching":[] if matching==30 else ["team-1"]}

class CombineTests(unittest.TestCase):
    def test_verified_seasons(self):
        r=combine([stage(2020,"a"),stage(2021,"b")],{2020:audit(2020),2021:audit(2021)})
        self.assertEqual(r["total_games"],2)
        self.assertEqual(r["status"],"VERIFIED_STAGING_NO_PUBLICATION")
    def test_failed_audit_blocks(self):
        with self.assertRaises(ValueError):
            combine([stage(2020,"a")],{2020:audit(2020,29)})
    def test_missing_audit_blocks(self):
        with self.assertRaises(ValueError):
            combine([stage(2020,"a")],{})
    def test_duplicate_season_blocks(self):
        with self.assertRaises(ValueError):
            combine([stage(2020,"a"),stage(2020,"b")],{2020:audit(2020)})
if __name__=="__main__":unittest.main()
