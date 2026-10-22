import copy
import json
import unittest
from pathlib import Path
from build_mlb_team_rankings import build, rate

class MLBTeamRankingsTests(unittest.TestCase):
    def test_direction_and_ties(self):
        rows = [dict(games_played=1, metrics=dict(run_diff_per_game=d,ops=o,era=e),
                     ratings={},ranks={}) for d,o,e in [(2,.8,3),(2,.7,4),(-1,.8,5)]]
        rate(rows)
        self.assertEqual([r['ranks']['overall'] for r in rows],[1,1,3])
        self.assertEqual([r['ranks']['offense'] for r in rows],[1,3,1])
        self.assertEqual([r['ranks']['defense'] for r in rows],[1,2,3])
        self.assertGreater(rows[0]['ratings']['defense_sd'],0)

    def test_missing_and_zero_games_are_not_ranked(self):
        rows=[dict(games_played=n,metrics=dict(run_diff_per_game=d,ops=o,era=e),
                   ratings={},ranks={}) for n,d,o,e in [(0,0,.9,2),(1,1,None,3)]]
        rate(rows)
        self.assertTrue(all(v is None for v in rows[0]['ranks'].values()))
        self.assertIsNone(rows[1]['ranks']['offense'])
        self.assertEqual(rows[1]['ranks']['defense'],1)

    def test_real_archive_and_no_source_mutation(self):
        root=Path(__file__).resolve().parents[1]
        source=json.loads((root/'data/mlb/season-snapshots.json').read_text())
        registry=json.loads((root/'data/sports/team-registry.json').read_text())
        before=copy.deepcopy(source)
        result=build(source,registry)
        self.assertEqual(source,before)
        self.assertEqual(len(result['seasons']),len(source['seasons']))
        for year,season in result['seasons'].items():
            self.assertEqual(len(season['teams']),30)
            for row in season['teams']:
                raw=source['seasons'][year][row['slug']]
                self.assertAlmostEqual(row['metrics']['run_diff_per_game'],
                    (raw['runs_scored']-raw['runs_allowed'])/raw['games_played'])
                self.assertAlmostEqual(row['metrics']['ops'],round(
                    raw['team_stats']['on_base_percentage']+raw['team_stats']['slugging_percentage'],3))
                self.assertNotIn('bullpen_era',row['metrics'])
        broken=copy.deepcopy(source)
        broken['seasons']['2026'].pop(next(iter(broken['seasons']['2026'])))
        with self.assertRaises(ValueError):
            build(broken,registry)

if __name__=='__main__':
    unittest.main()
