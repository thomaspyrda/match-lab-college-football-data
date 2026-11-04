#!/usr/bin/env python3
"""Read-only CBB freshness, provenance, score and publication checks. No provider calls."""
import json
from datetime import datetime, timezone
from pathlib import Path
import run_cbb_pipeline as p


def require_morning_collection(collected_at, now):
    from zoneinfo import ZoneInfo
    local = now.astimezone(ZoneInfo('America/New_York'))
    if local.hour >= 6:
        boundary = local.replace(hour=4, minute=0, second=0, microsecond=0)
        observed = datetime.fromisoformat(collected_at.replace('Z', '+00:00'))
        if observed < boundary:
            raise ValueError('CBB morning results collection is missing; prior-evening data is not a completed daily refresh')


def verify():
    components = {name: p.load(name, hours=30) for name in ('results', 'boxes', 'players', 'metrics', 'rosters')}
    results = components['results']
    require_morning_collection(results['collected_at'], datetime.now(timezone.utc))
    known = {str(t['espn_id']) for t in p.registry()}
    assert len(known) >= p.MIN_D1_TEAMS, 'Incomplete Division I membership'
    assert len(results['payload']['teams']) == len(known), 'Incomplete result coverage'
    for slug, observed in results['payload']['teams'].items():
        doc = p.read(p.ROOT / 'data/cbb/teams' / (slug + '.json'))
        assert str(doc['team_id']) == observed['team_id'], slug + ': wrong team'
        current = doc['seasons'][str(p.season())]
        for phase, source in observed['phases'].items():
            published = current['phases'][phase]
            for key in ('games', 'record', 'completed_games'):
                assert published[key] == source[key], slug + ': unpublished ' + phase + ' ' + key
    boxes = components['boxes']
    assert boxes['results_collected_at'] == results['collected_at'], 'Boxes have not caught up with results'
    assert components['players']['boxes_collected_at'] == boxes['collected_at'], 'Players have not processed latest boxes'
    assert components['metrics']['results_collected_at'] == results['collected_at'], 'Metrics have not processed latest results'
    games = boxes['payload']['games']
    assert len({str(g['id']) for g in games}) == len(games), 'Duplicate verified boxes'
    for game in games:
        assert game['season'] == p.season() and len(game['teams']) == 2, 'Wrong box season or teams'
        event = results['payload']['events'].get(str(game['id']))
        if event and event.get('status', {}).get('type', {}).get('completed'):
            assert {str(i): b['points'] for i, b in game['teams'].items()} == p.scores(event), 'Published box scores disagree with results'
    for kind, names in [('status', ('results', 'boxes', 'players', 'rosters')),
                        ('archive-status', ('results', 'metrics', 'players', 'rosters')),
                        ('ranks-status', ('results', 'metrics')), ('leaders-status', ('results', 'players'))]:
        status = p.load(kind, hours=30)
        for name in names:
            assert status['payload']['components'].get(name) == components[name]['collected_at'], kind + ': stale ' + name
    data = p.read(p.ROOT / 'cbb/dashboard/data/dashboard.json')
    assert data['schema_version'] == 2 and len(data['teams']) >= p.MIN_D1_TEAMS, 'Dashboard contract changed'
    assert len({g['id'] for g in data['games']}) == len(data['games']), 'Duplicate upcoming matchup'
    finals = p.read(p.ROOT / 'cbb/dashboard/data/completed-games.json')['games']
    assert {str(g['id']) for g in finals} == {str(g['id']) for g in games if set(g['teams']) <= known}, 'Dashboard finals do not match verified D1 boxes'
    assert data['completed_games'] == len(finals), 'Dashboard final count differs'
    ledger = p.read(p.ROOT / f'data/cbb/strength-games/{p.season()}.json')
    rankings = p.read(p.ROOT / 'data/cbb/strength-rankings.json')
    assert rankings['season'] == ledger['season'] == p.season(), 'Wrong strength season'
    assert rankings['games_evaluated'] == len(ledger['games']), 'Strength has not evaluated current ledger'
    assert (datetime.now(timezone.utc) - datetime.fromisoformat(rankings['updated_at'].replace('Z', '+00:00'))).total_seconds() <= 30 * 3600, 'Stale strength rankings'
    ranks = p.read(p.ROOT / 'data/cbb/metric-ranks.json')['seasons']
    has_finals = any(phase['completed_games'] for t in results['payload']['teams'].values() for phase in t['phases'].values())
    if has_finals:
        assert str(p.season()) in ranks, 'Missing active metric ranks'
    leaders = p.read(p.ROOT / 'data/cbb/division-one-season-leaders.json')['seasons']
    assert str(p.season()) in leaders, 'Missing current leaders dataset'
    report = dict(season=p.season(), teams=len(known), verified_boxes=len(games), upcoming_matchups=len(data['games']),
                  strength_games=len(ledger['games']), pending_strength=len(ledger.get('pending_games', [])),
                  pending_boxes=len(boxes.get('pending', [])), pending_players=len(components['players'].get('pending', [])),
                  retained_schedules=len(results.get('retained_schedules', [])), retained_rosters=len(components['rosters'].get('retained', [])))
    print(json.dumps(report, sort_keys=True))
    return report


if __name__ == '__main__':
    verify()
