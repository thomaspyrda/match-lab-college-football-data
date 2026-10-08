import unittest
from build_fbs_leaders import aggregate
from leaderboard_core import categories
class Tests(unittest.TestCase):
 def box(self,gid,team,yards):return dict(id=gid,teams=[dict(team=team,categories=[dict(name='passing',types=[dict(name='YDS',athletes=[dict(id='1',name='QB',stat=str(yards))]),dict(name='C/ATT',athletes=[dict(id='1',name='QB',stat='10/20')])])])])
 def test_completed_fbs_filter(self):
  p=aggregate([self.box(1,'Georgia',100),self.box(2,'Georgia',900),self.box(1,'FCS',500)],{'1'},{'Georgia'})[0];self.assertEqual(p['stats']['passing_yards'],100);self.assertEqual(p['stats']['attempts'],20)
 def test_missing_games(self):
  with self.assertRaises(ValueError):aggregate([self.box(1,'Georgia',100)],{'1','2'},{'Georgia'})
 def test_duplicate_rows(self):
  with self.assertRaises(ValueError):aggregate([self.box(1,'Georgia',100)]*2,{'1'},{'Georgia'})
 def test_average_minimum(self):
  p=[dict(id='a',name='A',teams={'Georgia'},games_played=1,stats={'passing_yards':500}),dict(id='b',name='B',teams={'Georgia'},games_played=3,stats={'passing_yards':900})];c=next(c for c in categories(p,2,True) if c['metric']=='passing_yards' and c['group']=='averages');self.assertEqual(c['players'][0]['value'],300)
