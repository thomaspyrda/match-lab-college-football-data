import unittest
from build_ap_elo import ap_by_week,rank_elos,weekly_elo_boards
class BuildTests(unittest.TestCase):
 def test_tied_elo_midpoint(self):
  b=rank_elos({"A":1600,"B":1600,"C":1500,"D":1400},4)
  self.assertEqual((b["A"]["strength_score"],b["B"]["strength_score"]),(83,83))
  self.assertEqual(b["D"]["strength_score"],1)
 def test_tiers(self):
  b=rank_elos({f"T{i}":2000-i for i in range(101)},101)
  self.assertEqual(b["T0"]["strength_tier"],"Elite")
  self.assertEqual(b["T50"]["strength_tier"],"Above Average")
  self.assertEqual(b["T100"]["strength_tier"],"Weak")
 def test_ap_tie_at_25(self):
  ranks=[{"rank":i,"school":f"T{i}"} for i in range(1,26)]+[{"rank":25,"school":"T25b"}]
  self.assertEqual(len(ap_by_week([{"season":2019,"week":2,"polls":[{"poll":"AP Top 25","ranks":ranks}]}])[2]),26)
if __name__=="__main__":unittest.main()
