#!/usr/bin/env python3
"""Read-only CFB cross-page verification after dependent producers finish."""
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

# Direct CLI execution starts with scripts/, so expose the repository package root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_cfb_pipeline import load, read

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    store = root / 'data/cfb/pipeline'
    results = load(store, 'results', max_hours=30)
    from scripts.morning_results import require_morning_results
    require_morning_results(results['collected_at'], datetime.now(timezone.utc), 'CFB')
    components = {name: load(store, name) for name in ['strength', 'metrics', 'players']}
    expected = set(results['completed_game_ids'])
    board = read(root / 'data/current_rankings.json')
    assert int(board['season']) == results['season'], 'Published CFB rankings have wrong season'
    assert int(board['through_week']) == results['through_week'], 'Published CFB rankings do not match verified result week'
    assert len(board['teams']) >= 130, 'Incomplete published FBS ranking pool'
    leaders = read(root / 'data/cfb-season-leaders.json')
    assert expected <= set(map(str, leaders['completed_game_ids'])), 'Season Leaders missing verified completed games'
    details = read(root / f'data/cfb/details/{results["season"]}.json')
    archived = {str(g['game_id']) for g in details['games'] if g.get('result')}
    assert expected <= archived, 'Team pages missing verified completed games'
    dashboard = read(root / 'cfb-dashboard-preview/data/dashboard.json')
    assert dashboard['games'], 'Published CFB dashboard is empty'
    status = read(store / 'status.json')
    assert status['components']['results']['collected_at'] == results['collected_at'], 'Dashboard has not published the latest verified results'
    for name, document in components.items():
        assert status['components'][name]['collected_at'] == document['collected_at'], 'Dashboard input publication is pending: ' + name
    assert datetime.fromisoformat(dashboard['slate']['generated_at']) >= datetime.fromisoformat(results['collected_at']), 'Dashboard is older than verified results'
    assert len({str(g['game_id']) for g in dashboard['games']}) == len(dashboard['games']), 'Duplicate dashboard matchups'
    for game in dashboard['games']:
        assert len(game['players']) == 10, 'Player card contract changed'
        assert len(game['matchup_metrics']) >= 11, 'Matchup metric contract changed'
        assert all(game[side].get('espn_id') for side in ['away', 'home']), 'Missing team identity'
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), read_only=True,
                  result_week=results['through_week'], verified_games=len(expected),
                  dashboard_games=len(dashboard['games']),
                  components={name: {'collected_at': doc['collected_at'], 'through_week': doc.get('through_week')}
                              for name, doc in components.items()})
    print(json.dumps(report, indent=2))
    return report


if __name__ == '__main__':
    verify()
