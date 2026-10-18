import unittest
from reconcile_mlb_player_team_hitting import reconcile
def stage():
 return {"season":2025,"team_datasets":[{"team_id":"144","groups":{"hitting":{"records":[{"stats":{"atBats":10,"hits":4,"homeRuns":1,"rbi":2}}]}}}]}
def api(url):
 return {"stats":[{"splits":[{"stat":{"atBats":10,"hits":4,"homeRuns":1,"rbi":2}}]}]}
class TotalsTests(unittest.TestCase):
 def test_matching_totals(self):
  r=reconcile(stage(),api)
  self.assertEqual(r["teams_matching"],1)
 def test_mismatch_reported(self):
  def wrong(url):
   r=api(url);r["stats"][0]["splits"][0]["stat"]["hits"]=5;return r
  self.assertIn("hits",reconcile(stage(),wrong)["teams"]["144"]["mismatches"])
 def test_missing_totals_rejected(self):
  with self.assertRaisesRegex(ValueError,"Missing or ambiguous"):reconcile(stage(),lambda u:{"stats":[]})
if __name__=="__main__":unittest.main()
