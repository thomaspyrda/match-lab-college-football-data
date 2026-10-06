import unittest
from datetime import datetime, timezone
from build_cfb_team_pages import build_season, record_label

class ArchiveTests(unittest.TestCase):
 def game(self,id='one',home=20,away=17,spread=-3,total=37,neutral=False):
  return {'game_id':id,'week':1,'start_date':'2015-09-01T00:00:00Z','home_id':61,'away_id':333,
   'home':'Georgia','away':'Alabama','home_conference':'SEC','away_conference':'SEC',
   'home_profile':{'classification':'FBS'},'away_profile':{'classification':'FBS'},
   'conference_game':True,'neutral_site':neutral,'spread':spread,'over_under':total,
   'result':{'home_points':home,'away_points':away}}
 def test_pushes_team_spread_signs_neutral_and_week_one(self):
  d=build_season([self.game(neutral=True)],2015)
  self.assertEqual(d['61']['ats']['pushes'],1);self.assertEqual(d['333']['games'][0]['spread'],3)
  self.assertEqual(d['61']['ou']['pushes'],1);self.assertEqual(d['61']['neutral']['wins'],1)
  self.assertEqual(d['61']['home']['wins'],0);self.assertEqual(d['61']['games'][0]['week'],1)
 def test_missing_lines_excluded_and_fcs_results_included(self):
  g=self.game(spread=None,total=None);g['away_profile']['classification']='FCS/Other'
  d=build_season([g],2015);self.assertEqual(d['61']['games_played'],1)
  self.assertEqual(d['61']['ats']['games'],0);self.assertNotIn('333',d)
 def test_primary_rank_direction_and_away_cover(self):
  d=build_season([self.game(home=20,away=30)],2015)
  self.assertEqual(d['61']['ats']['second'],1);self.assertEqual(d['333']['ats']['first'],1)
  self.assertEqual(d['333']['ppg_rank'],1);self.assertEqual(d['333']['ppg_allowed_rank'],1)
 def test_duplicates_and_future_results_rejected(self):
  with self.assertRaises(ValueError):build_season([self.game(),self.game()],2015)
  with self.assertRaises(ValueError):build_season([self.game()],2015,datetime(2014,1,1,tzinfo=timezone.utc))
 def test_tied_scoring_ranks_and_uncompleted_games(self):
  g=self.game(home=20,away=20);unfinished=self.game(id='two');unfinished['result']=None
  d=build_season([g,unfinished],2015)
  self.assertEqual(d['61']['ppg_rank'],1);self.assertEqual(d['333']['ppg_rank'],1)
  self.assertEqual(record_label(d['61']['record']),'0-0-1');self.assertEqual(d['61']['games_played'],1)
if __name__=='__main__':unittest.main()
