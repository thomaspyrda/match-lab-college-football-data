import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

CODE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE))
spec = importlib.util.spec_from_file_location('cbb_pipeline', CODE / 'scripts/run_cbb_pipeline.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class CBBPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(p, 'ROOT', self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.minimum = patch.object(p, 'MIN_D1_TEAMS', 2)
        self.minimum.start()
        self.addCleanup(self.minimum.stop)
        self.now = datetime.now(timezone.utc)
        self.year = p.season()
        self.teams = [dict(sport='cbb', slug=slug, espn_id=tid, id='cbb:team:' + slug,
                           name=name, abbreviation=name, logo='logo') for slug, tid, name in [('a', '1', 'A'), ('b', '2', 'B')]]
        p.write(self.root / 'data/sports/team-registry.json', {'teams': self.teams})
        self.final = self.event('g1', True, self.now - timedelta(days=1))
        self.future = self.event('g2', False, self.now + timedelta(days=1))
        self.summary = self.make_summary()
        schedules = {}
        for tid, slug, own, other in [('1', 'a', 80, 75), ('2', 'b', 75, 80)]:
            game = dict(id='g1', date=self.final['date'], opponent_id='2' if tid == '1' else '1',
                        opponent='B' if tid == '1' else 'A', opponent_name='B' if tid == '1' else 'A',
                        location='Home' if tid == '1' else 'Away', points=own, opponent_points=other,
                        result='W' if own > other else 'L', status='final', source_url='fixture')
            phases = {'regular': dict(games=[game], record={'wins': int(own > other), 'losses': int(own < other)},
                        completed_games=1, metrics={}), 'postseason': dict(games=[], record={'wins': 0, 'losses': 0}, completed_games=0, metrics={})}
            schedules[slug] = dict(team_id=tid, phases=phases, verified_at=self.now.isoformat())
            old = dict(key='2016', phases={'regular': {'games': [], 'completed_games': 0, 'metrics': {}}}, sentinel='frozen history')
            doc = dict(team_id=tid, slug=slug, seasons={'2016': old, str(self.year): dict(key=str(self.year), phases=copy.deepcopy(phases), players=[], coaches=['Existing coach'])})
            p.write(self.root / 'data/cbb/teams' / (slug + '.json'), doc)
        self.schedules = schedules
        self.save_results()

    def event(self, gid, final, when):
        competitors = [dict(id=tid, homeAway=side, score=score, team={'id': tid, 'displayName': name, 'color': '123456'})
                       for tid, side, name, score in [('1', 'home', 'A', '80'), ('2', 'away', 'B', '75')]]
        return dict(id=gid, date=when.isoformat(), season={'year': self.year, 'type': 2},
                    status={'type': {'completed': final, 'description': 'Final' if final else 'Scheduled'}},
                    competitions=[dict(competitors=competitors, neutralSite=False, type={'abbreviation': 'STD'})])

    def make_summary(self):
        teams = []
        players = []
        for tid, pts, fg, th, ft in [('1', 80, '30-60', '8-20', '12-16'), ('2', 75, '28-60', '6-20', '13-18')]:
            values = {'fieldGoalsMade-fieldGoalsAttempted': fg, 'threePointFieldGoalsMade-threePointFieldGoalsAttempted': th,
                      'freeThrowsMade-freeThrowsAttempted': ft, 'offensiveRebounds': '8', 'defensiveRebounds': '24',
                      'totalRebounds': '32', 'assists': '18', 'totalTurnovers': '10', 'steals': '6', 'blocks': '4', 'pointsInPaint': '30'}
            teams.append({'team': {'id': tid}, 'statistics': [{'name': k, 'displayValue': v} for k, v in values.items()]})
            keys = ['minutes', 'points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers', 'plusMinus',
                    'fieldGoalsMade-fieldGoalsAttempted', 'threePointFieldGoalsMade-threePointFieldGoalsAttempted', 'freeThrowsMade-freeThrowsAttempted']
            player = dict(athlete={'id': 'p' + tid, 'displayName': 'Player ' + tid, 'position': {'abbreviation': 'G'}},
                          stats=['35', str(pts), '8', '6', '2', '1', '2', '5', fg, th, ft])
            players.append({'team': {'id': tid}, 'statistics': [{'keys': keys, 'athletes': [player]}]})
        return dict(header={'season': {'year': self.year}, 'competitions': [{**self.final['competitions'][0],
                    'status': {'type': {'completed': True}}}]}, boxscore={'teams': teams, 'players': players})

    def save_results(self):
        p.save('results', {'teams': self.schedules, 'events': {'g1': self.final, 'g2': self.future}})

    def boxes(self, summary=None):
        with patch.object(p.dashboard, 'get', return_value=summary or self.summary):
            p.collect_boxes()

    def test_result_collection_does_not_request_players_metrics_or_rosters(self):
        def schedule(tid, year, phase):
            return copy.deepcopy(self.schedules['a' if tid == '1' else 'b']['phases']['regular']['games']) if phase == 2 else []
        with patch.object(p.archives, 'schedule', side_effect=schedule), \
             patch.object(p.archives, 'league', side_effect=AssertionError('No league-stat dependency')), \
             patch.object(p.dashboard, 'get', return_value={'events': [self.final, self.future]}):
            p.collect_results()
        result = p.load('results')
        self.assertEqual(result['payload']['teams']['a']['phases']['regular']['completed_games'], 1)
        self.assertFalse(result['retained_schedules'])

    def test_empty_schedule_cannot_erase_known_results(self):
        before = copy.deepcopy(p.load('results')['payload']['teams']['a'])
        with patch.object(p.archives, 'schedule', return_value=[]), patch.object(p.dashboard, 'get', return_value={'events': []}):
            p.collect_results()
        self.assertEqual(p.load('results')['payload']['teams']['a'], before)
        self.assertEqual(len(p.load('results')['retained_schedules']), 2)

    def test_box_normalization_matches_existing_collector(self):
        with patch.object(p.dashboard, 'get', return_value=self.summary):
            expected = p.dashboard.completed(self.final)
        self.boxes()
        actual = p.load('boxes')['payload']['games'][0]
        self.assertEqual(actual['teams'], expected['teams'])
        self.assertEqual(actual['home'], expected['home'])
        self.assertEqual(actual['market'], expected['market'])

    def test_player_outage_does_not_block_team_metrics(self):
        summary = copy.deepcopy(self.summary)
        summary['boxscore']['players'] = []
        self.boxes(summary)
        with patch.object(p.archives, 'league', return_value={}):
            p.collect_players()
        with patch.object(p.archives, 'get', side_effect=AssertionError('Full boxes require no season-stat request')):
            p.collect_metrics()
        self.assertTrue(p.load('players')['pending'])
        self.assertEqual(p.load('metrics')['payload']['teams']['a']['regular']['metrics']['points'], 80)

    def test_pending_players_are_retried_even_when_scores_are_unchanged(self):
        summary = copy.deepcopy(self.summary)
        summary['boxscore']['players'] = []
        self.boxes(summary)
        with patch.object(p.archives, 'league', return_value={}):
            p.collect_players()
        self.assertTrue(p.load('players')['pending'])
        self.boxes()
        p.collect_players()
        self.assertFalse(p.load('players')['pending'])
        self.assertEqual(p.read(p.chunk('players', 'g1'))['players']['1'][0]['name'], 'Player 1')

    def test_score_disagreement_is_quarantined(self):
        summary = copy.deepcopy(self.summary)
        summary['header']['competitions'][0]['competitors'][0]['score'] = '79'
        self.boxes(summary)
        self.assertFalse(p.load('boxes')['payload']['games'])
        self.assertEqual(p.load('boxes')['pending'][0]['id'], 'g1')

    def test_original_metric_and_player_math_and_frozen_history_are_preserved(self):
        self.boxes()
        p.collect_players()
        p.collect_metrics()
        expected = self.root / 'expected'
        shutil_copy = __import__('shutil').copytree
        shutil_copy(self.root / 'data/cbb/teams', expected)
        normalized = copy.deepcopy(p.load('boxes')['payload']['games'])
        normalized[0]['players'] = p.read(p.chunk('players', 'g1'))['players']
        p.enrichment.enrich(expected, normalized, self.year)
        projected = p.project(self.root / 'actual')
        for slug in ['a', 'b']:
            before = p.read(expected / (slug + '.json'))
            after = p.read(projected / (slug + '.json'))
            self.assertEqual(before['seasons']['2016'], after['seasons']['2016'])
            self.assertEqual(before['seasons'][str(self.year)]['phases']['regular']['metrics'], after['seasons'][str(self.year)]['phases']['regular']['metrics'])
            self.assertEqual(before['seasons'][str(self.year)]['players'], after['seasons'][str(self.year)]['players'])

    def test_verified_season_stats_can_fill_a_delayed_box_without_player_feed(self):
        p.save('boxes', {'games': []})
        def source(url):
            pts = 80 if '/teams/1/' in url else 75
            return {'splits': {'categories': [{'stats': [{'name': 'gamesPlayed', 'value': 1}, {'name': 'points', 'value': pts}, {'name': 'avgPoints', 'value': pts}]}]}}
        with patch.object(p.archives, 'get', side_effect=source):
            p.collect_metrics()
        record = p.load('metrics')['payload']['teams']['a']['regular']
        self.assertEqual(record['game_ids'], ['g1'])
        self.assertEqual(record['metrics']['points'], 80)

    def test_market_publication_has_no_statistical_or_result_dependency(self):
        (p.store() / 'results.json').unlink()
        path = self.root / 'cbb/dashboard/data/dashboard.json'
        data = {'teams': {'1': {'abbr': 'A', 'profile': {'record': '1–0'}}, '2': {'abbr': 'B'}},
                'games': [{'id': 'g2', 'home': '1', 'away': '2', 'metrics': [{'key': 'efg'}], 'market': {}}]}
        p.write(path, data)
        p.write(self.root / f'data/cbb/pregame-markets/{self.year}.json', {'games': {'g2': {'home_spread': 4.5, 'total': 150, 'provider': 'Observed', 'observed_at': self.now.isoformat()}}})
        with patch.object(p.dashboard, 'get', side_effect=AssertionError('No provider requests')):
            p.publish_markets()
        after = p.read(path)
        self.assertEqual(after['teams'], data['teams'])
        self.assertEqual(after['games'][0]['metrics'], data['games'][0]['metrics'])
        self.assertEqual(after['games'][0]['market']['spread'], 'B -4.5')

    def test_roster_failure_retains_existing_snapshot_and_is_retried(self):
        p.save('rosters', {'teams': {'1': {'roster': {'team_id': '1', 'observed_at': None, 'players': []}, 'coaches': []}}})
        with patch.object(p.archives, 'get', side_effect=OSError('Roster feed unavailable')):
            p.collect_rosters()
        self.assertEqual(len(p.load('rosters')['retained']), 2)

    def test_stale_results_block_new_ranking_inputs(self):
        doc = p.load('results')
        doc['collected_at'] = (self.now - timedelta(hours=12)).isoformat()
        p.write(p.store() / 'results.json', doc)
        with self.assertRaisesRegex(ValueError, 'Stale CBB input'):
            p.strength_inputs()

    def test_historical_market_rejects_unverified_late_quote(self):
        game = dict(id='g1', date=self.final['date'], market={'observed_at': self.now.isoformat(), 'home_spread': -5})
        self.assertIsNone(p.verified_market(game, {}))
        quote = dict(observed_at=self.now.isoformat(), tipoff=self.final['date'], home_spread=-5, total=150)
        self.assertIsNone(p.verified_market(game, {'g1': quote}))
        quote['source_type'] = 'archived_provider'
        self.assertEqual(p.verified_market(game, {'g1': quote})['home_spread'], -5)

    def test_stale_metrics_cannot_render_current_strength_columns(self):
        p.save('metrics', {'teams': {}}, results_collected_at='old')
        with self.assertRaisesRegex(ValueError, 'caught up'):
            p.publish_strength()

    def test_full_dashboard_assembly_is_offline_and_preserves_existing_formulas(self):
        extra = [dict(sport='cbb', slug='team' + str(i), espn_id=str(i), id='cbb:team:' + str(i),
                      name='Team ' + str(i), abbreviation='T' + str(i), logo='logo') for i in range(3, 351)]
        p.write(self.root / 'data/sports/team-registry.json', {'teams': self.teams + extra})
        self.boxes()
        p.collect_players()
        rosters = {tid: {'roster': {'team_id': tid, 'observed_at': self.now.isoformat(), 'source': 'fixture',
                    'players': [{'id': 'cbb:espn:player:p' + tid, 'name': 'Player ' + tid, 'position': 'G', 'headshot': None}]}, 'coaches': []} for tid in ['1', '2']}
        p.save('rosters', {'teams': rosters})
        with patch.object(p.dashboard, 'get', side_effect=AssertionError('Offline assembly')), \
             patch.object(p.dashboard, 'completed', side_effect=AssertionError('No re-collection of finals')), \
             patch.object(p.dashboard, 'roster', side_effect=AssertionError('No roster provider dependency')):
            p.assemble()
        data = p.read(self.root / 'cbb/dashboard/data/dashboard.json')
        self.assertEqual(data['schema_version'], 2)
        self.assertEqual(data['completed_games'], 1)
        self.assertEqual(len(data['games']), 1)
        self.assertEqual(data['teams']['1']['profile']['ppg'], 80)
        self.assertEqual(data['teams']['1']['roster'][0]['per_game']['points'], 80)


class CBBHealthTests(unittest.TestCase):
    setUp = CBBPipelineTests.setUp
    event = CBBPipelineTests.event
    make_summary = CBBPipelineTests.make_summary
    save_results = CBBPipelineTests.save_results
    boxes = CBBPipelineTests.boxes
    # Exercise the same on-disk contract used by the read-only live check.
    def prepare_health(self):
        self.boxes()
        p.collect_players()
        p.collect_metrics()
        p.save('rosters', {'teams': {}})
        snapshots = {name: p.load(name) for name in ('results', 'boxes', 'players', 'metrics', 'rosters')}
        for kind in ('status', 'archive-status', 'ranks-status', 'leaders-status'):
            p.save(kind, {'components': {name: doc['collected_at'] for name, doc in snapshots.items()}})
        games = snapshots['boxes']['payload']['games']
        p.write(self.root / 'cbb/dashboard/data/completed-games.json', {'games': games})
        p.write(self.root / 'cbb/dashboard/data/dashboard.json', {'schema_version': 2, 'teams': {'1': {}, '2': {}}, 'games': [], 'completed_games': 1})
        p.write(self.root / f'data/cbb/strength-games/{self.year}.json', {'season': self.year, 'games': games})
        p.write(self.root / 'data/cbb/strength-rankings.json', {'season': self.year, 'games_evaluated': 1, 'updated_at': self.now.isoformat()})
        p.write(self.root / 'data/cbb/metric-ranks.json', {'seasons': {str(self.year): {}}})
        p.write(self.root / 'data/cbb/division-one-season-leaders.json', {'seasons': {str(self.year): {}}})
        spec = importlib.util.spec_from_file_location('health_check', CODE / 'scripts/verify_cbb_pipeline.py')
        health = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'run_cbb_pipeline': p}):
            spec.loader.exec_module(health)
        return health

    def test_live_health_accepts_matching_publication(self):
        self.assertEqual(self.prepare_health().verify()['verified_boxes'], 1)

    def test_live_health_rejects_unpublished_results(self):
        health = self.prepare_health()
        status = p.load('status')
        status['payload']['components']['results'] = 'old'
        p.write(p.store() / 'status.json', status)
        with self.assertRaisesRegex(AssertionError, 'stale results'):
            health.verify()

    def test_live_health_rejects_incorrect_published_record(self):
        health = self.prepare_health()
        path = self.root / 'data/cbb/teams/a.json'
        doc = p.read(path)
        doc['seasons'][str(self.year)]['phases']['regular']['record']['wins'] = 9
        p.write(path, doc)
        with self.assertRaisesRegex(AssertionError, 'unpublished regular record'):
            health.verify()


class MorningCollectionTests(unittest.TestCase):
    def guard(self):
        spec = importlib.util.spec_from_file_location('morning_health', CODE / 'scripts/verify_cbb_pipeline.py')
        health = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'run_cbb_pipeline': p}):
            spec.loader.exec_module(health)
        return health.require_morning_collection

    def test_prior_evening_snapshot_fails_morning_check(self):
        with self.assertRaisesRegex(ValueError, 'morning results collection is missing'):
            self.guard()('2026-11-04T02:18:55+00:00', datetime(2026, 11, 4, 12, tzinfo=timezone.utc))

    def test_current_morning_snapshot_passes(self):
        self.guard()('2026-11-04T09:30:00+00:00', datetime(2026, 11, 4, 12, tzinfo=timezone.utc))

    def test_early_check_allows_morning_collection_window(self):
        self.guard()('2026-11-04T02:18:55+00:00', datetime(2026, 11, 4, 10, tzinfo=timezone.utc))


if __name__ == '__main__':
    unittest.main()
