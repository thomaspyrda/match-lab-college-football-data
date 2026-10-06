import unittest
from datetime import datetime,timezone
import refresh_mlb_dashboard as mlb
import refresh_cbb_dashboard as cbb
class SourceBoundaries(unittest.TestCase):
 def test_mlb_requested_phase_is_checked(self):
  fixture={'season':{'year':2026,'type':3},'requestedSeason':{'year':2026,'type':2},'results':{'stats':{'categories':[{'name':'batting','stats':[{'name':'teamGamesPlayed','value':162}]}]}}}
  self.assertEqual(mlb.categories(fixture,2026,2)['batting']['teamGamesPlayed'],162)
  self.assertEqual(mlb.categories(fixture,2026,3),{})
  self.assertEqual(mlb.categories(fixture,2025,2),{})
 def test_unplayed_mlb_teams_unranked(self):
  self.assertTrue(all(v is None for v in mlb.profile({})['metrics'].values()))
 def test_competition_rank_and_direction(self):
  p={a:{'metrics':{'ERA':b}} for a,b in [('A',3.0),('B',3.0),('C',4.0),('D',None)]}
  r=mlb.ranking(p,'ERA',False)
  self.assertEqual([r[x]['rank'] for x in ['A','B','C']],[1,1,3]);self.assertNotIn('D',r)
 def test_cbb_season_phases_stay_separate(self):
  games=[{'season':2027,'phase':1},{'season':2027,'phase':2},{'season':2026,'phase':2}]
  self.assertEqual(cbb.season_history(games,2027,2),[games[1]])
 def test_cbb_unplayed_profile_has_no_zero_rank(self):
  p=cbb.profile('61',[],datetime.now(timezone.utc))
  self.assertEqual(p['record'],'—');self.assertIsNone(p['metrics']['ortg']);self.assertEqual(cbb.rank({'61':p},'ortg',True),{})
if __name__=='__main__':unittest.main()
