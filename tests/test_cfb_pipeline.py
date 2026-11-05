"""Regression checks for preserved calculations, offline assembly, and outage isolation."""
import copy
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import chdir
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

CODE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cfb_runner', CODE / 'scripts/run_cfb_pipeline.py')
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)
SOURCE = Path.cwd()
if not (SOURCE / 'cfb_dashboard/pipeline/build_dashboard.py').exists():
    SOURCE = CODE / 'foundation'
sys.path.insert(0, str(SOURCE))
NOW = datetime.now(timezone.utc)
YEAR = NOW.year


class FixedDate(datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW if tz else NOW.replace(tzinfo=None)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'work'
        self.main = Path(self.temp.name) / 'main'
        self.root.mkdir()
        self.main.mkdir()
        self.store = self.main / 'data/cfb/pipeline'
        self.store.mkdir(parents=True)
        self.parts = pipeline.split_source((SOURCE / 'refresh_match_lab.py').read_text())
        self.teams = ['A', 'B'] + [f'Team {n}' for n in range(138)]
        self.metadata = {name: dict(espn_id=i + 1, abbr=name, logo='logo', conference='ACC') for i, name in enumerate(self.teams)}
        self.raw_final = dict(id=1, season=YEAR, week=1, seasonType='regular', completed=True,
            homeTeam='A', awayTeam='B', homePoints=28, awayPoints=21,
            startDate=(NOW - timedelta(days=2)).isoformat())
        self.future = dict(id=2, season=YEAR, week=2, seasonType='regular', completed=False,
            homeTeam='A', awayTeam='B', homePoints=None, awayPoints=None,
            startDate=(NOW + timedelta(days=1)).isoformat())
        self.history = [dict(game_id='1', week=1, home='A', away='B', start_date=self.raw_final['startDate'],
                             result={'home_points': 28, 'away_points': 21})]
        self.upcoming = dict(game_id='2', season=YEAR, week=2, home='A', away='B', start_date=self.future['startDate'])
        self.files = {
            'data/current_rankings.json': dict(season=YEAR, week=2, model={'version': 'v15'},
                                                teams=[dict(team=t) for t in self.teams]),
            'data/upcoming.json': {'games': [self.upcoming]},
            'data/cfb_dashboard_team_metadata.json': {'teams': self.metadata},
            f'data/historical/{YEAR}.json': {'games': self.history},
        }
        self.responses = {
            pipeline.query_key('/games', dict(year=YEAR, seasonType='regular')): [self.raw_final, self.future],
            pipeline.query_key('/teams/fbs', dict(year=YEAR)): [dict(school=t, id=i + 1) for i, t in enumerate(self.teams)],
        }
        self.results = dict(files=self.files, responses=self.responses, team_games=[self.raw_final, self.future])
        pipeline.save(self.store, 'results', self.results, completed_game_ids=['1'], through_week=1)
        self.env = patch.dict(os.environ, CFBD_API_KEY='fixture-only')
        self.env.start()
        self.addCleanup(self.env.stop)

    def provider(self, path, **params):
        if path == '/stats/season/advanced':
            return [dict(team=t, season=YEAR, offense={'ppa': 0.2, 'successRate': .45},
                         defense={'ppa': .1, 'successRate': .4}) for t in self.teams]
        if path == '/player/usage':
            return [dict(id=i + 1, name=t + ' QB', team=t, position='QB', usage={'overall': .4, 'pass': 1})
                    for i, t in enumerate(self.teams)]
        if path == '/stats/player/season':
            return [dict(playerId=i + 1, player=t + ' QB', team=t, category='passing', statType=key, stat=value)
                    for i, t in enumerate(self.teams) for key, value in [('YDS', 300), ('ATT', 30), ('CMP', 20), ('TD', 2)]]
        if path == '/roster':
            return [dict(id=i + 1, team=t, position='QB') for i, t in enumerate(self.teams)]
        if path == '/stats/season':
            return [dict(team=t, statName=key, statValue=value) for t in self.teams
                    for key, value in [('totalYards', 400), ('netPassingYards', 300), ('rushingYards', 100)]]
        return []

    def namespace(self, root, common):
        ns = self.original_namespace(root, common)
        ns['api'] = self.provider
        return ns

    def baseline(self, component):
        folder = Path(self.temp.name) / 'baseline'
        folder.mkdir(exist_ok=True)
        pipeline.restore_results(folder, pipeline.load(self.store, 'results'))
        ns = self.original_namespace(folder, self.parts['common'])
        ns.update(api=self.provider, now=NOW, last_completed=1, current_records=self.history,
                  team_meta=self.metadata, fbs_teams=set(self.metadata))
        from cfb_dashboard.pipeline import availability
        with patch.object(availability, 'fetch_reports', return_value={}):
            exec(compile(self.parts[component], str(SOURCE / 'refresh_match_lab.py'), 'exec'), ns)
        name = 'cfb_dashboard_raw_metrics.json' if component == 'metrics' else 'cfb_dashboard_player_usage.json'
        return pipeline.read(folder / 'data' / name)

    def test_metrics_match_existing_collector_calculations(self):
        self.original_namespace = pipeline.namespace
        expected = self.baseline('metrics')
        with patch.object(pipeline, 'namespace', self.namespace), patch.object(pipeline, 'datetime', FixedDate), \
             patch.object(pipeline, 'request', self.provider), patch.object(pipeline.runpy, 'run_path', return_value={'enrich': lambda p: p}):
            pipeline.collect_statistics(self.root, self.store, 'metrics', self.parts)
        actual = pipeline.load(self.store, 'metrics')['payload']['dashboard']
        self.assertEqual(expected, actual)

    def test_players_match_existing_collector_calculations(self):
        self.original_namespace = pipeline.namespace
        expected = self.baseline('players')
        with patch.object(pipeline, 'namespace', self.namespace), patch.object(pipeline, 'datetime', FixedDate), \
             patch.object(pipeline, 'request', self.provider):
            pipeline.collect_statistics(self.root, self.store, 'players', self.parts)
        self.assertEqual(expected, pipeline.load(self.store, 'players')['payload']['dashboard'])

    def test_swallowed_provider_error_cannot_replace_last_good_metrics(self):
        pipeline.save(self.store, 'metrics', {'known_good': True})
        before = (self.store / 'metrics.json').read_bytes()
        self.original_namespace = pipeline.namespace
        original = self.provider
        def outage(path, **params):
            if path == '/games/teams':
                raise OSError('simulated box-score outage')
            return original(path, **params)
        self.provider = outage
        with patch.object(pipeline, 'namespace', self.namespace), self.assertRaisesRegex(ValueError, 'retain last verified'):
            pipeline.collect_statistics(self.root, self.store, 'metrics', self.parts)
        self.assertEqual(before, (self.store / 'metrics.json').read_bytes())

    def test_results_stage_does_not_collect_metrics_or_players(self):
        for endpoint in ['/stats/season/advanced', '/games/teams', '/passing/plays', '/player/usage', '/stats/player/season']:
            self.assertNotIn('api("' + endpoint + '"', self.parts['schedule'])

    def test_verified_results_refresh_without_market_metric_or_player_feeds(self):
        pipeline.restore_results(self.root, pipeline.load(self.store, 'results'))
        weekly = {'season': YEAR, 'weeks': {'1': {'teams': {t: {'strength_score': 50 + i / 10} for i, t in enumerate(self.teams)}}}}
        pipeline.write(self.root / f'data/weekly/{YEAR}.json', weekly)
        calls = []
        def only_results(path, **params):
            calls.append(path)
            if path == '/games':
                games = [self.raw_final, dict(self.future, homePoints=7, awayPoints=0)]
                return [g for g in games if 'week' not in params or g['week'] == params['week']]
            if path == '/teams/fbs':
                return [dict(school=t, id=i + 1) for i, t in enumerate(self.teams)]
            if path == '/rankings':
                return []
            raise AssertionError('Results cannot depend on this feed: ' + path)
        self.original_namespace = pipeline.namespace
        self.provider = only_results
        with patch.object(pipeline, 'namespace', self.namespace):
            pipeline.collect_results(self.root, self.store, self.parts)
        pipeline.pack_results(self.root, self.store)
        snapshot = pipeline.load(self.store, 'results')
        self.assertEqual(snapshot['completed_game_ids'], ['1'])
        self.assertEqual(snapshot['through_week'], 1)
        self.assertEqual(len(snapshot['payload']['files']['data/upcoming.json']['games']), 1)
        self.assertNotIn('/lines', calls)

    def test_approved_ranking_inputs_replay_verified_current_results(self):
        source = '''import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
def api(path, **params):
    raise AssertionError('Current games must come from verified input')
'''
        source += pipeline.BOUNDARY + '\n'
        source += f'''games=api('/games',year={YEAR},seasonType='regular')
(Path(__file__).parent/'captured-games.json').write_text(json.dumps(games))
'''
        (self.root / 'refresh_match_lab.py').write_text(source)
        pipeline.ranking_inputs(self.root, self.store)
        self.assertEqual(pipeline.read(self.root / 'captured-games.json'), [self.raw_final, self.future])

    def test_source_revision_drift_fails_closed(self):
        with self.assertRaisesRegex(ValueError, 'source revision changed'):
            pipeline.split_source((SOURCE / 'refresh_match_lab.py').read_text() + '# changed calculation')

    def test_partial_scores_are_not_final_results(self):
        row = dict(self.future, homePoints=7, awayPoints=0)
        result = pipeline.verified_games([row])[0]
        self.assertIsNone(result['homePoints'])
        self.assertIsNone(result['awayPoints'])
        self.assertEqual(row['homePoints'], 7)

    def test_unscored_complete_record_is_excluded_without_blocking_verified_games(self):
        rows = pipeline.verified_games([self.raw_final, dict(self.future, id=401907219, completed=True, homePoints=None)])
        self.assertTrue(rows[0]['completed'])
        self.assertEqual(rows[0]['homePoints'], 28)
        self.assertFalse(rows[1]['completed'])
        self.assertIsNone(rows[1]['homePoints'])
        self.assertEqual(rows[1]['verification_issue'], 'provider_complete_without_valid_scores')

    def test_numeric_provider_scores_are_normalized_and_duplicate_ids_rejected(self):
        row = pipeline.verified_games([dict(self.raw_final, homePoints='28', awayPoints='21')])[0]
        self.assertTrue(row['completed'])
        self.assertEqual(row['homePoints'], 28)
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            pipeline.verified_games([self.raw_final, self.raw_final])

    def test_old_result_snapshot_cannot_feed_rankings(self):
        path = self.store / 'results.json'
        doc = pipeline.read(path)
        doc['collected_at'] = (NOW - timedelta(hours=12)).isoformat()
        pipeline.write(path, doc)
        with self.assertRaisesRegex(ValueError, 'Stale CFB input'):
            pipeline.load(self.store, 'results', max_hours=8)

    def test_historical_market_fallback_preserves_real_quotes(self):
        path = self.root / f'data/historical/{YEAR}.json'
        pipeline.write(path, {'games': [dict(self.history[0], spread=-3.5, over_under=47.5, provider='Consensus')]})
        rows = pipeline.cached_lines(self.root, None, dict(year=YEAR, week=1))
        self.assertEqual(rows[0]['lines'][0]['spread'], -3.5)
        self.assertEqual(rows[0]['lines'][0]['overUnder'], 47.5)

    def test_market_refresh_changes_only_game_market_fields(self):
        data = {'slate': {'model_version': 'v15'}, 'games': [dict(game_id='2', players=[{'name': 'QB'}],
                    away={'team_strength': 75}, matchup_metrics=[{'value': .5}], market={'total': 40})]}
        before = copy.deepcopy(data)
        pipeline.apply_markets(data, {'collected_at': NOW.isoformat(), 'payload': {'season_lines': [{'id': '2', 'lines': [dict(provider='Consensus', spread=-4, overUnder=49)]}], 'weeks': {}}})
        before['games'][0]['market'] = data['games'][0]['market']
        self.assertEqual(before, data)
        self.assertEqual(data['games'][0]['market']['spread'], -4)

    def test_live_market_publication_survives_missing_statistical_snapshots(self):
        (self.store / 'results.json').unlink()
        path = self.root / 'cfb-dashboard-preview/data/dashboard.json'
        original = {'slate': {'model_version': 'v15'}, 'games': [{'game_id': '2', 'players': [{'name': 'Keep Player'}],
                     'away': {'team_strength': 75}, 'market': {'total': 40}}]}
        pipeline.write(path, original)
        pipeline.save(self.store, 'markets', {'season_lines': [{'id': 2, 'lines': [{'provider': 'Consensus', 'spread': -4.5, 'overUnder': 49}]}], 'weeks': {}})
        with patch.object(pipeline.urllib.request, 'urlopen', side_effect=AssertionError('Quote publication must be offline')):
            pipeline.publish_markets(self.root, self.store)
        after = pipeline.read(path)
        self.assertEqual(after['games'][0]['market']['spread'], -4.5)
        self.assertEqual(after['games'][0]['players'], original['games'][0]['players'])
        self.assertEqual(after['games'][0]['away'], original['games'][0]['away'])

    def test_missing_metrics_does_not_touch_published_dashboard(self):
        live = self.root / 'cfb_dashboard/data/dashboard.json'
        pipeline.write(live, {'known_good': True})
        before = live.read_bytes()
        pipeline.save(self.store, 'strength', {'board': self.files['data/current_rankings.json']})
        with self.assertRaisesRegex(ValueError, 'Missing verified CFB input: metrics'):
            pipeline.assemble(self.root, self.store)
        self.assertEqual(before, live.read_bytes())

    def test_team_page_metrics_and_leaders_match_existing_collector(self):
        spec = importlib.util.spec_from_file_location('old_cfb_details', CODE / 'refresh_cfb_team_details.py')
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        sys.modules['refresh_cfb_team_details'] = old
        baseline = Path(self.temp.name) / 'team-baseline'
        historical = [dict(home=t, away='A', home_profile={'classification': 'FBS'}, away_profile={'classification': 'FBS'}) for t in self.teams]
        pipeline.write(baseline / f'data/historical/{YEAR}.json', {'games': historical})
        quote = {'id': 1, 'lines': [{'provider': 'Consensus', 'spread': -3.5, 'overUnder': 47.5}]}
        def api(path, **params):
            rows = self.results['team_games'] if path == '/games' else [quote] if path == '/lines' else self.provider(path, **params)
            return rows, 'fixture:' + path
        with patch.object(old, 'ROOT', baseline), patch.object(old, 'api', api):
            old.collect(YEAR, force=True)
        expected = pipeline.read(baseline / f'data/cfb/details/{YEAR}.json')
        pipeline.write(self.root / f'data/cfb/details/{YEAR}.json', expected)
        pipeline.save(self.store, 'metrics', {'advanced': self.provider('/stats/season/advanced'), 'basic': self.provider('/stats/season')})
        pipeline.save(self.store, 'players', {'team_players': self.provider('/stats/player/season')})
        pipeline.save(self.store, 'markets', {'season_lines': [quote], 'weeks': {}})
        with patch.object(pipeline.urllib.request, 'urlopen', side_effect=AssertionError('Team-page assembly must be offline')):
            pipeline.team_pages(self.root, self.store)
        actual = pipeline.read(self.root / f'data/cfb/details/{YEAR}.json')
        self.assertEqual(expected['teams'], actual['teams'])
        self.assertEqual(expected['games'], actual['games'])
        self.assertEqual(expected['player_stat_catalog'], actual['player_stat_catalog'])
        self.assertEqual(expected['team_stat_catalog'], actual['team_stat_catalog'])

    def test_injury_snapshot_adapter_does_not_confirm_unlisted_players(self):
        path = self.main / 'data/dashboard-availability/cfb.json'
        pipeline.write(path, {'teams': {'1': {'state': 'reported', 'checked_at': NOW.isoformat(),
                       'players': [{'name': 'Known Player', 'status': 'Out', 'id': 'cfb:espn:player:123'}]}}})
        reports = pipeline.availability_reports(self.store)
        self.assertTrue(reports[('1', 'id:123')]['unavailable'])
        self.assertNotIn(('1', 'name:unlisted player'), reports)

    def test_dashboard_assembly_is_offline_and_preserves_strength_and_players(self):
        from cfb_dashboard.pipeline import build_dashboard as builder
        pipeline.save(self.store, 'strength', {'board': self.files['data/current_rankings.json']})
        pipeline.save(self.store, 'metrics', {'dashboard': {'teams': self.metadata}, 'play_mix': {'games': [], 'slate': {}},
            'advanced': self.provider('/stats/season/advanced'),
            'basic': [dict(season=YEAR, team=t, statName=k, statValue=v) for t in self.teams
                      for k, v in [('games', 1), ('netPassingYards', 300), ('passCompletions', 20),
                                   ('rushingYards', 100), ('rushingAttempts', 25)]]})
        pipeline.save(self.store, 'players', {'dashboard': {'teams': self.metadata}})
        for filename in ['refresh_cfb_dashboard_schedule_only.py']:
            shutil.copy(CODE / filename, self.main / filename)
        (self.main / 'scripts').mkdir()
        shutil.copy(CODE / 'scripts/cfb_dashboard_yardage.py', self.main / 'scripts/cfb_dashboard_yardage.py')
        target = self.root / 'cfb_dashboard/pipeline/validate_launch.py'
        target.parent.mkdir(parents=True)
        shutil.copy(SOURCE / 'cfb_dashboard/pipeline/validate_launch.py', target)
        players = [dict(position=position, name=side + str(i), player_id=side + str(i), efficiency=None)
                   for side in ['A', 'B'] for i, position in enumerate(['QB', 'RB', 'WR', 'TE', 'WR'])]
        game = dict(game_id='2', season=YEAR, week=2, kickoff=self.future['startDate'],
                    home=dict(name='A', espn_id=1, team_strength=80), away=dict(name='B', espn_id=2, team_strength=60),
                    players=players, matchup_metrics=[dict(label='Baseline metric ' + str(i), away_offense=.5, home_defense=.5, home_offense=.5, away_defense=.5) for i in range(11)],
                    context={}, market={}, weather={}, trends=[])
        payload = dict(slate={'model_version': 'v15'}, games=[game])
        def build():
            pipeline.write(self.root / 'cfb_dashboard/data/dashboard.json', copy.deepcopy(payload))
        with chdir(self.root), patch.object(builder, 'main', side_effect=build), \
             patch.object(pipeline.urllib.request, 'urlopen', side_effect=AssertionError('Assembly must be offline')):
            pipeline.assemble(self.root, self.store)
        after = pipeline.read(self.root / 'cfb_dashboard/data/dashboard.json')
        self.assertEqual(after['games'][0]['players'], players)
        self.assertEqual(after['games'][0]['home']['team_strength'], 80)
        self.assertEqual(after['games'][0]['matchup_metrics'][:11], payload['games'][0]['matchup_metrics'])
        added = {m['label']: m for m in after['games'][0]['matchup_metrics'][11:]}
        self.assertEqual(added['Pass Yards/Game']['away_offense'], 300)
        self.assertEqual(added['Yards/Completion']['away_offense'], 15)
        self.assertEqual(added['Yards/Carry']['home_offense'], 4)
        self.assertTrue((self.root / 'cfb_dashboard/data/location-records.json').exists())
        self.assertEqual(pipeline.read(self.store / 'status.json')['game_count'], 1)


if __name__ == '__main__':
    unittest.main()
