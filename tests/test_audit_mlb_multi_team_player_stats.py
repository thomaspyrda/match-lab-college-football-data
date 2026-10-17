import unittest
from audit_mlb_multi_team_player_stats import audit
def sample(team):
 return {"season":2025,"team_id":str(team),"groups":{"hitting":{"records":[
 {"season":2025,"player_id":7,"team_id":str(team),"attribution":"explicit_team_split","stats":{"hits":4}}]}}}
class MultiTeamTests(unittest.TestCase):
 def test_shared_player_keeps_both_team_splits(self):
  r=audit([sample(144),sample(147)])
  self.assertEqual(r["records"],2)
  self.assertEqual(r["cross_team_players"][0]["teams"],["144","147"])
 def test_repeated_team_split_is_rejected(self):
  with self.assertRaisesRegex(ValueError,"Duplicate"):audit([sample(144),sample(144)])
 def test_attribution_mismatch_rejected(self):
  a=sample(144);a["groups"]["hitting"]["records"][0]["team_id"]="147"
  with self.assertRaisesRegex(ValueError,"Unverified"):audit([a,sample(147)])
if __name__=="__main__":unittest.main()
