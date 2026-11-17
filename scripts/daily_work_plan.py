"""Detect new verified finals before starting expensive sport calculations.

Only the lightweight source check runs unconditionally. Watermarks advance only
after that sport's dependent jobs succeed. Failures never become 'no change'.
"""
import argparse
import csv
import io
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
ET = ZoneInfo('America/New_York')
LEAGUES = {'nba': 'basketball/nba', 'cbb': 'basketball/mens-college-basketball'}
STATE = 'data/automation/daily-watermarks.json'
PLAN = 'data/automation/daily-plan.json'

def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default

def get(url, token=None):
    headers = {'User-Agent': 'WiseStats-primary-source-check/1', 'Cache-Control': 'no-cache'}
    if token: headers['Authorization'] = 'Bearer '+token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as response:
        return response.read().decode()

def espn_finals(board):
    out = {}
    for event in board.get('events', []):
        comp = event.get('competitions', [{}])[0]
        if not comp.get('status', event.get('status', {})).get('type', {}).get('completed'): continue
        scores = {str(c['team']['id']): str(c.get('score')) for c in comp.get('competitors', [])}
        if len(scores) != 2 or any(v in ('None', '') for v in scores.values()):
            raise ValueError('Completed game has no verified score')
        out[str(event['id'])] = [list(pair) for pair in sorted(scores.items())]
    return out

def changed_finals(observed, previous):
    return {gid: score for gid, score in observed.items() if previous.get(gid) != score}

def verified_no_change(sport, root, now):
    plan = read(Path(root)/PLAN, {})
    item = plan.get('sports', {}).get(sport, {})
    state = read(Path(root)/STATE, {}).get('sports', {}).get(sport, {})
    try:
        checked = datetime.fromisoformat(plan['checked_at'])
        fresh = checked.astimezone(ET).date() == now.astimezone(ET).date() and timedelta(0) <= now-checked <= timedelta(hours=18)
    except (ValueError, KeyError, TypeError): return False
    return fresh and item.get('status') == 'checked' and item.get('statistics') is False and bool(state) and not changed_finals(item.get('observed_finals', {}), state.get('finals', {}))

def has_pending(root, sport):
    for component in ('results', 'boxes', 'players', 'metrics'):
        doc = read(root/f'data/{sport}/pipeline/{component}.json', {})
        if doc.get('pending') or doc.get('retained_schedules'): return True
    return False

def make_plan(root=ROOT, now=None, fetch=get):
    now = now or datetime.now(timezone.utc)
    local = now.astimezone(ET)
    last_day = local.date()-timedelta(days=1)
    first_day = last_day-timedelta(days=2)
    old = read(root/STATE, {'sports': {}})
    # Catch every missed day after an outage, not just a fixed recent window.
    for prior in old.get('sports', {}).values():
        if prior.get('checked_through'):
            first_day = min(first_day, datetime.fromisoformat(prior['checked_through']).date())
    plan = {'schema': 1, 'checked_at': now.isoformat(), 'checked_through': str(last_day), 'sports': {}}
    for sport in ('nba', 'cbb', 'cfb', 'nfl'):
        previous = old.get('sports', {}).get(sport, {})
        try:
            if sport in LEAGUES:
                url = 'https://site.api.espn.com/apis/site/v2/sports/'+LEAGUES[sport]+'/scoreboard?limit=1000&dates='+first_day.strftime('%Y%m%d')+'-'+last_day.strftime('%Y%m%d')
                if sport == 'cbb': url += '&groups=50'
                observed = espn_finals(json.loads(fetch(url)))
            elif sport == 'cfb':
                key = os.environ.get('CFBD_API_KEY')
                if not key: raise ValueError('CFB source credential is unavailable')
                rows = json.loads(fetch('https://api.collegefootballdata.com/games?year='+str(local.year)+'&seasonType=regular', key))
                if not isinstance(rows, list): raise ValueError('CFB source returned an invalid schedule')
                observed = {str(g['id']): [g['homePoints'], g['awayPoints']] for g in rows if g.get('completed') and g.get('homePoints') is not None and g.get('awayPoints') is not None and str(g.get('startDate', ''))[:10] <= str(last_day)}
            else:
                rows = list(csv.DictReader(io.StringIO(fetch('https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv'))))
                observed = {r['game_id']: [r['home_score'], r['away_score']] for r in rows if r.get('season') == str(local.year) and r.get('game_type') == 'REG' and r.get('home_score') not in ('', 'NA', None) and r.get('away_score') not in ('', 'NA', None) and r.get('gameday', '9999') <= str(last_day)}
            changed = changed_finals(observed, previous.get('finals', {}))
            pending = has_pending(root, sport) if sport in ('cbb', 'cfb') else False
            stats = bool(changed or pending)
            leaders = stats
            if sport == 'nfl':
                nfl = root/'.sources/nfl/data'
                rankings = read(nfl/'nfl-rankings.json', {})
                current = read(nfl/'nfl-season-leaders.json', {})
                stats |= set(observed)-set(rankings.get('completed_game_ids', [])) != set()
                leaders = stats or set(rankings.get('completed_game_ids', [])) != set(current.get('completed_game_ids', []))
            plan['sports'][sport] = {'status': 'checked', 'statistics': stats, 'leaders': leaders, 'changed_finals': sorted(changed), 'pending_inputs': pending, 'observed_finals': observed}
        except Exception as exc:
            # A failed check must never authorize an off-day skip or mark data fresh.
            plan['sports'][sport] = {'status': 'source_unavailable', 'statistics': True, 'leaders': True, 'reason': type(exc).__name__}
    return plan

def checkpoint(root, results):
    plan = read(root/PLAN)
    state = read(root/STATE, {'schema': 1, 'sports': {}})
    for sport, item in plan['sports'].items():
        if item['status'] == 'checked' and results.get(sport) in ('success', 'unchanged'):
            prior = state['sports'].get(sport, {})
            state['sports'][sport] = {'checked_through': plan['checked_through'], 'checked_at': plan['checked_at'], 'finals': {**prior.get('finals', {}), **item.get('observed_finals', {})}}
    path = root/STATE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, sort_keys=True, separators=(',', ':'))+'\n')
    receipt = {'schema': 1, 'checked_at': plan['checked_at'], 'checked_through': plan['checked_through'], 'sports': {}}
    now = datetime.now(timezone.utc)
    for sport, item in plan['sports'].items():
        ready = results.get(sport) == 'success' or verified_no_change(sport, root, now)
        receipt['sports'][sport] = {'status': 'ready' if ready else 'pending', 'statistics_changed': item['statistics'], 'completed_game_ids': sorted(item.get('observed_finals', {}))}
    (root/'data/daily-readiness.json').write_text(json.dumps(receipt, sort_keys=True, separators=(',', ':'))+'\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', action='store_true')
    args = parser.parse_args()
    if args.checkpoint:
        checkpoint(ROOT, json.loads(os.environ['SPORT_RESULTS']))
        return
    plan = make_plan()
    path = ROOT/PLAN
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, sort_keys=True, separators=(',', ':'))+'\n')
    output = os.environ.get('GITHUB_OUTPUT')
    for sport, item in plan['sports'].items():
        print(sport, item['status'], 'statistics='+str(item['statistics']), 'new finals='+str(len(item.get('changed_finals', []))))
        if output:
            with open(output, 'a') as handle:
                handle.write(sport+'='+str(item['statistics']).lower()+'\n')
                if sport == 'nfl': handle.write('nfl_leaders='+str(item['leaders']).lower()+'\n')

if __name__ == '__main__': main()
