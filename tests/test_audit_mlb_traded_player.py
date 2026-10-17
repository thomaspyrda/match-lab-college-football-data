import unittest
from audit_mlb_traded_player import compare
def sample(team):
 return {"season":2023,"team_id":str(team),"groups":{"hitting":{"records":[{"player_id":664056,"team_id":str(team),"attribution":"explicit_team_split","stats":{"gamesPlayed":22}}]}}}
class TradedPlayerTests(unittest.TestCase):
 def test_distinct_team_splits(self):
  r=compare(sample(147),sample(113),664056)
  self.assertEqual(r["team_ids"],["147","113"])
 def test_ambiguous_team_blocked(self):
  a=sample(147); b=sample(113)
  b["groups"]["hitting"]["records"][0]["attribution"]="unknown"
  with self.assertRaisesRegex(ValueError,"Ambiguous"):compare(a,b,664056)
 def test_missing_player_blocked(self):
  a=sample(147); b=sample(113);b["groups"]["hitting"]["records"]=[]
  with self.assertRaisesRegex(ValueError,"exactly one"):compare(a,b,664056)
if __name__=="__main__":unittest.main()
