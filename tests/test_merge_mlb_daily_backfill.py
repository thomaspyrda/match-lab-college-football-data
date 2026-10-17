import unittest
from merge_mlb_daily_backfill import merge_archive
def sample():
 m={str(x):{"slug":f"team-{x}"} for x in range(1,31)}
 g={"game_id":"123","date":"2026-10-17","game_type":"L","home":{"id":"1","runs":5},"away":{"id":"2","runs":3},"players":{"home":[{"player_id":3}],"away":[{"player_id":4}]},"source":"MLB Stats API"}
 return {"status":"STAGED_NOT_PUBLISHED","games":{"123":g}},{"teams":m}
class TestMLBMerge(unittest.TestCase):
 def test_idempotence_and_phase(self):
  st,cw=sample();first,n=merge_archive({"games":{}},st,cw)
  self.assertEqual(n["inserted"],1)
  self.assertEqual(first["games"]["123"]["phase"],"league_championship")
  second,n=merge_archive(first,st,cw)
  self.assertEqual(n["existing"],1)
 def test_conflicting_result_rejected(self):
  st,cw=sample();first,_=merge_archive({"games":{}},st,cw)
  st["games"]["123"]["home"]["runs"]=9
  with self.assertRaises(ValueError):merge_archive(first,st,cw)
 def test_unknown_team_rejected(self):
  st,cw=sample();st["games"]["123"]["home"]["id"]="999"
  with self.assertRaises(ValueError):merge_archive({"games":{}},st,cw)
if __name__=="__main__":unittest.main()
