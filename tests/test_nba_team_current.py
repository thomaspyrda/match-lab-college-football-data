import copy,json,unittest
from pathlib import Path
from build_nba_team_current import build, ROOT

class CurrentTeams(unittest.TestCase):
    def test_current_pages_reconcile_and_do_not_mutate_inputs(self):
        cache=json.loads((ROOT/'nba/dashboard/data/completed-games.json').read_text())
        registry=json.loads((ROOT/'data/sports/team-registry.json').read_text())
        before=copy.deepcopy(cache)
        result=build(cache,registry)
        self.assertEqual(cache,before)
        self.assertEqual(len(result['teams']),30)
        self.assertEqual(sum(t['games_played'] for t in result['teams'].values()),2*result['completed_games'])
        for t in result['teams'].values():
            self.assertEqual(t['key'],'2027')
            if not t['games_played']:
                self.assertEqual(t['record']['overall'],'0–0')
                self.assertIsNone(t['metrics']['ppg'])
                self.assertEqual(t['players'],[])
            else:
                self.assertIsNotNone(t['metrics']['points_allowed_per_game'])
                self.assertTrue(t['players'])
                for p in t['players']:
                    self.assertAlmostEqual(p['per_game']['points']*p['games'],p['totals']['points'])
    def test_other_seasons_excluded(self):
        registry=json.loads((ROOT/'data/sports/team-registry.json').read_text())
        result=build({'games':[{'season':2026,'phase':2},{'season':2027,'phase':3}]},registry)
        self.assertEqual(result['completed_games'],0)
        self.assertTrue(all(t['record']['overall']=='0–0' for t in result['teams'].values()))
