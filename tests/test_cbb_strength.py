import copy,json,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from build_cbb_strength import calculate,anchor_weight,weighted_mean,non_d1_penalty,possessions
ROOT=Path(__file__).resolve().parents[1]
class StrengthTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.seed=json.loads((ROOT/'data/cbb/preseason/2027.json').read_text());cls.reg=json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'];cls.now=datetime(2026,12,20,tzinfo=timezone.utc)
 def game(self,a,b,index=0,home=None,neutral=True,pa=80,pb=70):
  def box(p):return {'points':p,'fgm':p/2,'fga':80,'tpm':0,'ftm':0,'fta':0,'oreb':10,'tov':10}
  return {'id':str(index),'date':(datetime(2026,11,1,18,tzinfo=timezone.utc)+timedelta(days=index)).isoformat(),'season':2027,'phase':2,'home':home or a,'neutral':neutral,'teams':{a:box(pa),b:box(pb)}}
 def calc(self,games):return calculate(self.seed,{'season':2027,'games':games},self.reg,self.now)[0]
 def test_preseason_complete_average_order(self):
  out=self.calc([]);self.assertEqual(len(out['teams']),365)
  self.assertEqual([t['team_id'] for t in out['teams']],[t['team_id'] for t in self.seed['teams']])
  self.assertAlmostEqual(sum(t['strength_score'] for t in out['teams'])/365,50)
  self.assertTrue(all(t['offensive_rating'] is None and t['preseason_weight']==1 for t in out['teams']))
 def test_twelve_game_decay_and_recent_weights(self):
  self.assertEqual([anchor_weight(n) for n in (0,3,6,9,12,15)],[1,.75,.5,.25,0,0])
  self.assertGreater(weighted_mean([0]*7+[10]),weighted_mean([10]+[0]*7))
  self.assertAlmostEqual(weighted_mean([1]*20),1)
  games=[self.game('150','57',n) for n in range(12)];out=self.calc(games)
  self.assertEqual(next(t for t in out['teams'] if t['team_id']=='150')['preseason_weight'],0)
 def test_opponent_adjustment_rewards_identical_play_vs_stronger_defense(self):
  a=self.calc([self.game('150','57')]);b=self.calc([self.game('150',self.seed['teams'][-1]['team_id'])])
  get=lambda x:next(t['offensive_rating'] for t in x['teams'] if t['team_id']=='150')
  self.assertGreater(get(a),get(b))
 def test_home_advantage_neutralized(self):
  get=lambda x:next(t['net_efficiency'] for t in x['teams'] if t['team_id']=='150')
  self.assertLess(get(self.calc([self.game('150','57',neutral=False)])),get(self.calc([self.game('150','57')])) )
 def test_no_future_opponent_information(self):
  first=self.game('150','57');second=self.game('57','12',1,pa=100,pb=60)
  _,a=calculate(self.seed,{'season':2027,'games':[first]},self.reg,self.now)
  _,b=calculate(self.seed,{'season':2027,'games':[first,second]},self.reg,self.now)
  self.assertEqual(a,b[:2])
 def test_non_d1_penalty_does_not_decay_or_inflate_units(self):
  g=self.game('150','outside',pa=80,pb=70);g['opponent_classification']='verified_non_d1'
  row=next(t for t in self.calc([g])['teams'] if t['team_id']=='150')
  self.assertEqual(row['d1_games'],0);self.assertEqual(row['preseason_weight'],1);self.assertIsNone(row['offensive_rating']);self.assertEqual(row['non_d1_penalty'],1)
  self.assertEqual(non_d1_penalty(15),0)
  self.assertTrue(non_d1_penalty(14)<non_d1_penalty(10)<non_d1_penalty(5)<non_d1_penalty(-1)<non_d1_penalty(-20))
 def test_incomplete_box_or_unverified_final_blocks_publication(self):
  g=self.game('150','57');g['teams']['150']['oreb']=None
  with self.assertRaises(ValueError):self.calc([g])
  with self.assertRaises(ValueError):calculate(self.seed,{'season':2027,'games':[],'pending_games':[{}]},self.reg,self.now)
 def test_duplicates_and_future_results_rejected(self):
  g=self.game('150','57')
  with self.assertRaises(ValueError):self.calc([g,g])
  g['date']='2027-01-01T00:00:00+00:00'
  with self.assertRaises(ValueError):self.calc([g])
if __name__=='__main__':unittest.main()
