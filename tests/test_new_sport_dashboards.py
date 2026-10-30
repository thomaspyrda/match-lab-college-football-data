import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from pathlib import Path
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
class SeasonMarkets(unittest.TestCase):
 def test_cbb_season_is_not_last_five(self):
  history=[{'date':f'2026-10-{day:02d}T00:00:00Z','observed_complete_at':'2026-10-29T00:00:00Z','home':'a','teams':{'a':{'points':80},'b':{'points':70}},'market':{'observed_at':'2026-10-29T00:00:00Z','home_spread':-5,'total':140}} for day in range(1,8)]
  with patch.object(cbb,'derived_metrics',return_value={}):p=cbb.profile('a',history,datetime(2026,10,30,tzinfo=timezone.utc))
  self.assertEqual(p['season_market']['ats']['wins'],7)
  self.assertEqual(p['season_market']['ou']['overs'],7)
  self.assertEqual(p['last5_market']['ats']['wins'],5)
 def test_mlb_season_filters_phase_and_counts_pushes(self):
  def event(i,phase,score):return {'id':i,'date':'2026-04-01T00:00:00Z','season':{'year':2026,'type':phase},'status':{'type':{'completed':True}},'competitions':[{'competitors':[{'team':{'id':'a'},'homeAway':'home','score':str(score)},{'team':{'id':'b'},'homeAway':'away','score':'3'}]}]}
  events=[event('1',2,5),event('2',2,4),event('3',3,9)]
  def source(url,optional=False):return {'events':events} if url.startswith('scoreboard') else {'pickcenter':[{'overUnder':8,'spread':1.5,'homeTeamOdds':{'favorite':True}}]}
  with TemporaryDirectory() as folder,patch.object(mlb,'ROOT',Path(folder)),patch.object(mlb,'get',side_effect=source):
   result=mlb.season_market_records(2026,2,datetime(2026,10,30,tzinfo=timezone.utc),{'a','b'})
  self.assertEqual(result['a']['ats'],{'wins':1,'losses':1,'pushes':0,'lined_games':2})
  self.assertEqual(result['a']['ou'],{'overs':0,'unders':1,'pushes':1,'lined_games':2})
  self.assertEqual(result['b']['ats']['wins'],1)
if __name__=='__main__':unittest.main()
