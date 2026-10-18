import unittest
from select_mlb_player_leaders import choose

def fixture():
 def row(i,stats,group):
  return {"player_id":i,"team_id":"144","attribution":"explicit_team_split","stats":stats,"group":group}
 return {"team_id":"144","season":2025,"complete":True,"groups":{
  "hitting":{"records":[row(i,{"atBats":i*10,"hits":i},"hitting") for i in range(1,26)]},
  "pitching":{"records":[row(i,{"gamesPlayed":30,"gamesStarted":20 if i<=8 else 0},"pitching") for i in range(1,22)]}}}
class LeadersTests(unittest.TestCase):
 def test_top_hitters_and_distinct_pitchers(self):
  x=choose(fixture())
  self.assertEqual(len(x["top_hitters"]),20)
  self.assertEqual(x["top_hitters"][0]["player_id"],25)
  self.assertEqual(len(x["starting_pitchers"]),8)
  self.assertEqual(len(x["relief_pitchers"]),8)
  self.assertFalse({r["player_id"] for r in x["starting_pitchers"]}&{r["player_id"] for r in x["relief_pitchers"]})
 def test_wrong_team_rejected(self):
  x=fixture();x["groups"]["hitting"]["records"][0]["team_id"]="147"
  with self.assertRaisesRegex(ValueError,"Unverified"):choose(x)
 def test_missing_at_bats_rejected(self):
  x=fixture();del x["groups"]["hitting"]["records"][0]["stats"]["atBats"]
  with self.assertRaisesRegex(ValueError,"Missing atBats"):choose(x)
if __name__=="__main__":unittest.main()
