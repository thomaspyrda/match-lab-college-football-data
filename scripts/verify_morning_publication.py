#!/usr/bin/env python3
"""Check morning source readiness and actual public JSON, without rewriting data."""
import argparse
import concurrent.futures
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
HOST = 'https://matchlab.parlaycalculator.bet/'


def require_collection(value, now):
    observed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    local = now.astimezone(ZoneInfo('America/New_York'))
    boundary = local.replace(hour=2, minute=30, second=0, microsecond=0)
    if observed < boundary or observed > now:
        raise ValueError('No verified collection since 2:30 a.m. Eastern: ' + value)


def plan(sport, root, now):
    paths = []
    if sport == 'nfl':
        ranking = json.loads((root / 'data/nfl-rankings.json').read_text())
        require_collection(ranking['as_of'], now)
        paths = ['data/dashboard.json', 'data/nfl-rankings.json', 'data/nfl-season-leaders.json']
    elif sport == 'nba':
        dashboard = json.loads((root / 'nba/dashboard/data/dashboard.json').read_text())
        require_collection(dashboard['updated_at'], now)
        yesterday = (now.astimezone(ZoneInfo('America/New_York')).date()).toordinal() - 1
        from datetime import date
        if dashboard['freshness']['checked_through'] != str(date.fromordinal(yesterday)):
            raise ValueError('NBA has not checked all previous-day games')
        paths = ['nba/dashboard/data/dashboard.json', 'nba/dashboard/data/completed-games.json',
                 'nba/teams/data/current-season.json', 'nba/rankings/data/nba-team-rankings.json']
    else:
        names = ['results', 'boxes', 'players', 'metrics'] if sport == 'cbb' else ['results', 'metrics', 'players', 'strength']
        for name in names:
            component = json.loads((root / f'data/{sport}/pipeline/{name}.json').read_text())
            require_collection(component['collected_at'], now)
            if component.get('pending') or (name == 'results' and component.get('retained_schedules')):
                raise ValueError(sport + ' ' + name + ': source items are still pending; see component diagnostics')
        if sport == 'cbb':
            paths = ['cbb/dashboard/data/dashboard.json', 'cbb/dashboard/data/completed-games.json',
                     'data/cbb/strength-rankings.json', 'data/cbb/metric-ranks.json',
                     'data/cbb/division-one-season-leaders.json']
            paths += [str(p.relative_to(root)) for p in (root / 'data/cbb/teams').glob('*.json')]
        else:
            paths = ['cfb-dashboard-preview/data/dashboard.json', 'data/current_rankings.json',
                     'data/cfb-season-leaders.json', f'data/cfb/details/{now.year}.json']
    return paths


def compare(path, root, host, fetch=None):
    expected = json.loads((root / path).read_text())
    def request():
        url = host + path + '?morning_audit=' + str(time.time_ns())
        req = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'BetWise-Morning-Audit/1'})
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    actual = (fetch or request)()
    if actual != expected:
        raise ValueError(path + ': live publication differs from the repository snapshot')
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sport', choices=['all', 'cbb', 'cfb', 'nba', 'nfl'], default='all')
    args = parser.parse_args()
    sports = ['cbb', 'cfb', 'nba'] if args.sport == 'all' else [args.sport]
    failures = []
    for sport in sports:
        try:
            paths = plan(sport, ROOT, datetime.now(timezone.utc))
            host = 'https://nfl.parlaycalculator.bet/' if sport == 'nfl' else HOST
            # Hosting can lag a successful commit. Retry the entire snapshot check,
            # but never accept a timestamp alone as proof of deployment.
            for attempt in range(5):
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                        list(pool.map(lambda path: compare(path, ROOT, host), paths))
                    break
                except Exception:
                    if attempt == 4:
                        raise
                    time.sleep(15)
            print(sport + ': morning inputs ready; ' + str(len(paths)) + ' public files match')
        except Exception as exc:
            failures.append(sport + ': ' + str(exc))
    if failures:
        raise SystemExit('\n'.join(failures))


if __name__ == '__main__':
    main()
