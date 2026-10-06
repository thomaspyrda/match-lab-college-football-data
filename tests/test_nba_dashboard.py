import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

spec=importlib.util.spec_from_file_location('nba',Path(__file__).resolve().parents[1]/'refresh_nba_dashboard.py')
nba=importlib.util.module_from_spec(spec);spec.loader.exec_module(nba)

class NBADataTests(unittest.TestCase):
    def game(self,observed='2026-10-04T02:00:00+00:00'):
        own={'points':100,'fgm':40,'fga':80,'tpm':10,'tpa':30,'ftm':10,'fta':15,'oreb':10,'dreb':30,'reb':40,'ast':20,'tov':12,'stl':5,'blk':4}
        opp=dict(own,points=90,fgm=35)
        return {'id':'fixture','date':'2026-10-03T23:00:00Z','observed_complete_at':observed,'teams':{'1':own,'2':opp},'players':{},'home':'2','phase':1}
    def test_no_future_results_or_backdated_observations(self):
        p=nba.profile('1',[self.game()],datetime(2026,10,4,1,tzinfo=timezone.utc));self.assertEqual(p['games'],0);self.assertIsNone(p['metrics']['ortg'])
    def test_estimated_possessions_and_ratings(self):
        p=nba.profile('1',[self.game()],datetime(2026,10,5,tzinfo=timezone.utc));self.assertEqual(p['record'],'1–0');self.assertAlmostEqual(p['metrics']['ortg'],10000/88.6);self.assertAlmostEqual(p['metrics']['efg'],56.25)
    def test_unplayed_team_not_ranked(self):
        a=nba.profile('1',[self.game()],datetime(2026,10,5,tzinfo=timezone.utc));b=nba.profile('3',[self.game()],datetime(2026,10,5,tzinfo=timezone.utc));self.assertEqual(set(nba.rank({'1':a,'3':b},'ortg',True)),{'1'})
    def test_rank_direction_and_ties(self):
        profiles={i:{'metrics':{'x':v}} for i,v in [('a',10),('b',20),('c',10)]}
        ranks=nba.rank(profiles,'x',False);self.assertEqual(ranks['a']['rank'],1);self.assertEqual(ranks['c']['rank'],1);self.assertEqual(ranks['b']['rank'],3)
    def test_dnp_not_zero_stat_player(self):
        row={'statistics':[{'keys':['minutes','points'],'athletes':[{'didNotPlay':True,'athlete':{'id':'1'},'stats':['0','0']}]}]};self.assertEqual(nba.players_box(row),[])
    def test_player_plus_minus_is_averaged_from_available_games(self):
        g=self.game();g['players']={'1':[{'id':'player:1','name':'Fixture','position':'G','headshot':None,'minutes':20,'points':10,'rebounds':2,'assists':3,'turnovers':1,'plus_minus':6,'fgm':4,'fga':8,'tpm':1,'tpa':3,'ftm':1,'fta':2}]}
        p=nba.profile('1',[g],datetime(2026,10,5,tzinfo=timezone.utc));self.assertEqual(p['players'][0]['plus_minus'],6);self.assertIsNone(p['players'][0]['vorp'])
    def test_zero_attempt_shooting_is_missing(self):self.assertIsNone(nba.ratio(0,0,100))
    def test_seasons_and_preseason_never_mix(self):
        games=[{'id':'pre','season':2027,'phase':1},{'id':'reg','season':2027,'phase':2},{'id':'old','season':2026,'phase':2}]
        self.assertEqual([g['id'] for g in nba.season_history(games,2027,2)],['reg'])

if __name__=='__main__':unittest.main()
