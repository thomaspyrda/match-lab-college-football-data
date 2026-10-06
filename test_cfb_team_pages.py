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
class DetailTests(unittest.TestCase):
 def test_multi_category_leader_keeps_independent_ranks(self):
  from supplement_cfb_2015_defense import ranked_copy
  p=dict(id='a',stats=dict(combined_tackles=100,sacks=5))
  league={'combined_tackles':{'a':100,'b':120},'sacks':{'a':5,'b':4}}
  tackles=ranked_copy(p,'combined_tackles',league);sacks=ranked_copy(p,'sacks',league)
  self.assertEqual(tackles['league_total'],100);self.assertEqual(tackles['rank'],2)
  self.assertEqual(sacks['league_total'],5);self.assertEqual(sacks['rank'],1)
  self.assertNotIn('rank',p)
 def test_provider_third_down_denominators(self):
  from refresh_cfb_team_details import metric_pairs
  pairs=metric_pairs({},dict(thirdDownConversions=5,thirdDowns=10,thirdDownConversionsOpponent=3,thirdDownsOpponent=12))
  rate=next(p for p in pairs if p['label']=='3rd-down conversion rate')
  self.assertEqual(rate['offense'],.5);self.assertEqual(rate['defense'],.25)
 def player(self,pid,category,stat,value):
  return dict(team='Georgia',playerId=pid,player=pid,category=category,statType=stat,stat=value)
 def test_interceptions_primary_then_pd_then_touchdowns(self):
  from refresh_cfb_team_details import player_leaders
  rows=[self.player('a','interceptions','INT',3),self.player('a','defensive','PD',8),self.player('a','interceptions','TD',0),self.player('b','interceptions','INT',3),self.player('b','defensive','PD',7),self.player('b','interceptions','TD',2),self.player('c','interceptions','INT',2),self.player('c','defensive','PD',30)]
  d=player_leaders(rows,{'Georgia'});self.assertEqual(d['Georgia']['interceptions']['id'],'a')
  rows.extend([self.player('d','interceptions','INT',3),self.player('d','defensive','PD',8),self.player('d','interceptions','TD',1)])
  d=player_leaders(rows,{'Georgia'});self.assertEqual(d['Georgia']['interceptions']['id'],'d');self.assertEqual(d['Georgia']['interceptions']['rank'],1)
 def test_college_passing_rating_and_half_sacks(self):
  from refresh_cfb_team_details import player_leaders
  rows=[self.player('a','passing','YDS',100),self.player('a','passing','TD',1),self.player('a','passing','INT',1),self.player('a','passing','C/ATT','5/10'),self.player('b','defensive','SACKS',.5)]
  d=player_leaders(rows,{'Georgia'});self.assertEqual(d['Georgia']['passing']['stats']['passer_rating'],147)
  self.assertEqual(d['Georgia']['sacks']['league_total'],.5)
 def test_result_colors_and_metric_rank_directions(self):
  from cfb_team_sections import cls,rank_metrics
  self.assertEqual([cls(x) for x in ['W','L','O','U','P',None]],['result-w','result-l','result-w','result-l','result-p','result-p'])
  d={'Georgia':{'metrics':[dict(label='PPA per play',offense=.4,defense=.1)]},'Alabama':{'metrics':[dict(label='PPA per play',offense=.3,defense=.2)]}}
  rank_metrics(d);self.assertEqual(d['Georgia']['metrics'][0]['offense_rank'],1);self.assertEqual(d['Georgia']['metrics'][0]['defense_rank'],1)
 def test_postseason_result_and_upcoming_schedule(self):
  from cfb_team_sections import attach_details
  fixture=ArchiveTests();g=fixture.game();g.update(season_type='regular',notes='')
  post=fixture.game(id='post',home=30,away=10);post.update(season_type='postseason',notes='National Championship',start_date='2016-01-10T00:00:00Z')
  upcoming=fixture.game(id='future');upcoming.update(season_type='regular',notes='',result=None,start_date='2015-09-15T00:00:00Z')
  details=dict(year=2015,updated_at='2026-10-06',sources=[],games=[g,post,upcoming],teams={'Georgia':dict(coaches=[],metrics=[],leaders={})})
  registry={'61':dict(name='Georgia'),'333':dict(name='Alabama')}
  d=attach_details({},details,registry,build_season,2026)
  self.assertEqual(d['61']['games_played'],1);self.assertEqual(len(d['61']['schedule']),3)
  self.assertIn('National champions',d['61']['season_result_html'])
if __name__=='__main__':unittest.main()
