import unittest
from stage_mlb_league_player_stats import collect

def mapping():
 return {"teams":{str(i):{"slug":f"team-{i}"} for i in range(1,31)}}
def fake(url):
 group="hitting" if "group=hitting" in url else "pitching"
 tid=int(url.split("teamId=")[1].split("&")[0])
 return {"stats":[{"splits":[{"player":{"id":1000+tid,"fullName":"Player"},
 "team":{"id":tid},"stat":{"gamesPlayed":10,"atBats":25,"hits":7,"inningsPitched":"8.0","era":"3.00"}}]}]}
class LeagueTests(unittest.TestCase):
 def test_all_thirty_teams_staged(self):
  result=collect(2025,mapping(),fake)
  self.assertEqual(len(result["team_coverage"]),30)
  self.assertEqual(result["records"],60)
 def test_missing_core_fields_block(self):
  def missing(url):
   r=fake(url)
   if "group=pitching" in url:r["stats"][0]["splits"][0]["stat"].pop("era")
   return r
  with self.assertRaisesRegex(ValueError,"Core player stat missing"):collect(2025,mapping(),missing)
if __name__=="__main__":unittest.main()
