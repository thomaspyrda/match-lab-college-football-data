#!/usr/bin/env python3
"""Independent CBB inputs and offline publishers; existing calculations are reused."""
import argparse
import copy
import json
import math
import shutil
import sys
import tempfile
import types
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MIN_D1_TEAMS = 350
sys.path.insert(0, str(ROOT))
import backfill_cbb_team_archives as archives
import enrich_cbb_team_boxes as enrichment
import refresh_cbb_dashboard as dashboard


def season():
    now = datetime.now(ZoneInfo('America/New_York'))
    return now.year + (now.month >= 7)


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n')
    temp.replace(path)


def store():
    return ROOT / 'data/cbb/pipeline'


def save(component, payload, **metadata):
    write(store() / (component + '.json'), dict(schema_version=1, component=component, season=season(),
          collected_at=datetime.now(timezone.utc).isoformat(), payload=payload, **metadata))


def load(component, hours=None, required=True):
    path = store() / (component + '.json')
    if not path.exists():
        if not required:
            return None
        raise ValueError('Missing verified CBB input: ' + component)
    doc = read(path)
    if doc.get('schema_version') != 1 or doc.get('component') != component or doc.get('season') != season():
        raise ValueError('Invalid CBB input season/contract: ' + component)
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(doc['collected_at'])).total_seconds() / 3600
    if age < -0.1 or (hours is not None and age > hours):
        raise ValueError('Stale CBB input: ' + component)
    return doc


def registry():
    return [t for t in read(ROOT / 'data/sports/team-registry.json')['teams'] if t['sport'] == 'cbb']


def chunk(kind, gid):
    return store() / kind / str(season()) / (str(gid) + '.json')


def number(value):
    if isinstance(value, dict):
        value = value.get('value', value.get('displayValue'))
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def scores(event):
    competitors = event['competitions'][0]['competitors']
    result = {str(c['team']['id']): number(c.get('score')) for c in competitors}
    if len(result) != 2 or any(v is None or v < 0 for v in result.values()) or len(set(result.values())) != 2:
        raise ValueError('Unverified CBB final score: ' + str(event['id']))
    return result


def collect_results():
    year = season()
    teams = registry()
    known = {str(t['espn_id']) for t in teams}
    if len(known) < MIN_D1_TEAMS or len(known) != len(teams) or len({t['slug'] for t in teams}) != len(teams):
        raise ValueError('Incomplete Division I membership')
    previous = load('results', required=False)
    errors = []
    def one(team):
        tid = str(team['espn_id'])
        try:
            phases = {}
            prior = (previous or {}).get('payload', {}).get('teams', {}).get(team['slug'])
            canonical = ROOT / 'data/cbb/teams' / (team['slug'] + '.json')
            if prior is None and canonical.exists():
                old = read(canonical)
                if str(old['team_id']) != tid:
                    raise ValueError('CBB team identity changed')
                old = old.get('seasons', {}).get(str(year))
                prior = {'phases': old['phases']} if old else None
            for phase, label in ((2, 'regular'), (3, 'postseason')):
                games = archives.schedule(tid, year, phase)
                if not games and (prior or {}).get('phases', {}).get(label, {}).get('games'):
                    raise ValueError('Empty schedule cannot erase known games')
                done = [g for g in games if g['status'] == 'final']
                phases[label] = dict(games=games, record={'wins': sum(g['result'] == 'W' for g in done),
                    'losses': sum(g['result'] == 'L' for g in done)}, completed_games=len(done))
            return team['slug'], dict(team_id=tid, phases=phases, verified_at=datetime.now(timezone.utc).isoformat())
        except Exception as exc:
            errors.append({'team': team['slug'], 'error': str(exc)})
            old = (previous or {}).get('payload', {}).get('teams', {}).get(team['slug'])
            if old is not None:
                return team['slug'], old
            path = ROOT / 'data/cbb/teams' / (team['slug'] + '.json')
            canonical = read(path) if path.exists() else {}
            if canonical and str(canonical.get('team_id')) != tid:
                raise ValueError('CBB fallback team identity changed') from exc
            existing = canonical.get('seasons', {}).get(str(year))
            if existing is None:
                raise ValueError('No verified fallback schedule for ' + team['slug']) from exc
            return team['slug'], dict(team_id=tid, phases={k: {f: v for f, v in p.items() if f in ('games', 'record', 'completed_games')}
                                        for k, p in existing['phases'].items()}, verified_at=existing.get('collected_at'))
    with ThreadPoolExecutor(12) as pool:
        schedules = dict(pool.map(one, teams))
    now = datetime.now(ZoneInfo('America/New_York'))
    start = max(now.date() - timedelta(days=7), now.date().replace(year=year - 1, month=11, day=1))
    ledger = ROOT / f'data/cbb/strength-games/{year}.json'
    if ledger.exists() and read(ledger).get('last_scanned'):
        from datetime import date
        start = min(start, date.fromisoformat(read(ledger)['last_scanned']) - timedelta(days=6))
        start = max(start, now.date().replace(year=year - 1, month=11, day=1))
    end = now.date() + timedelta(days=7)
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    def board(day):
        raw = dashboard.get('scoreboard?groups=50&limit=1000&dates=' + day.strftime('%Y%m%d'))
        events = [e for e in raw.get('events', []) if e.get('season', {}).get('year') == year and
                  any(str(c['team']['id']) in known for c in e['competitions'][0]['competitors'])]
        write(store() / 'boards' / str(year) / (day.strftime('%Y%m%d') + '.json'), {'events': events})
        return events
    with ThreadPoolExecutor(6) as pool:
        events = {str(e['id']): e for rows in pool.map(board, days) for e in rows}
    save('results', {'teams': schedules, 'events': events}, retained_schedules=errors)
    print(json.dumps({'teams': len(schedules), 'events': len(events), 'retained_schedules': len(errors)}))


def cloned(function, **replacements):
    return types.FunctionType(function.__code__, dict(function.__globals__, **replacements),
                              function.__name__, function.__defaults__, function.__closure__)


def collect_boxes():
    results = load('results', hours=8)
    base = ROOT / 'cbb/dashboard/data/completed-games.json'
    old = {str(g['id']): g for g in read(base).get('games', []) if g['season'] == season()} if base.exists() else {}
    previous = load('boxes', required=False)
    games = {str(g['id']): g for g in (previous or {}).get('payload', {}).get('games', [])}
    games = {**old, **games}
    pending = []
    score_only = []
    known = {str(t['espn_id']) for t in registry()}
    if len(known) < MIN_D1_TEAMS:
        raise ValueError('Incomplete Division I membership')
    player_state = load('players', required=False)
    retry_players = {str(g['id']) for g in (player_state or {}).get('pending', [])}
    retry_boxes = {str(g['id']) for g in (previous or {}).get('pending', [])}
    retry_events = dict(results['payload']['events'])
    ledger = ROOT / f'data/cbb/strength-games/{season()}.json'
    if ledger.exists():
        for row in read(ledger).get('pending_games', []):
            event = row['event']
            retry_events.setdefault(str(event['id']), event)
    events = [e for e in retry_events.values() if e.get('status', {}).get('type', {}).get('completed')]
    def one(event):
        gid = str(event['id'])
        try:
            expected = scores(event)
            saved = games.get(gid)
            path = chunk('boxes', gid)
            if saved and path.exists() and {str(i): b.get('points') for i, b in saved['teams'].items()} == expected:
                raw = read(path)
                observed = datetime.fromisoformat(raw.get('_verified_at', '1970-01-01T00:00:00+00:00'))
                recent = dashboard.stamp(event['date']) >= datetime.now(timezone.utc) - timedelta(days=3)
                refresh = gid in retry_players or gid in retry_boxes or (recent and (datetime.now(timezone.utc) - observed).total_seconds() >= 6 * 3600)
                if not refresh:
                    return gid, saved
            summary = dashboard.get('summary?event=' + gid)
            header = (summary.get('header', {}).get('competitions') or [{}])[0]
            if not header.get('status', {}).get('type', {}).get('completed'):
                raise ValueError('Summary not final')
            got = {str(c['team']['id']): number(c.get('score')) for c in header.get('competitors', [])}
            if got != expected:
                raise ValueError('Schedule/summary scores disagree')
            if summary.get('header', {}).get('season', {}).get('year', season()) != season():
                raise ValueError('Wrong summary season')
            # Verified non-D1 finals may legitimately have no published box score.
            # Keep schedule/result facts; never manufacture team or player statistics.
            missing_team_box = any(not t.get('statistics') for t in summary.get('boxscore', {}).get('teams', [])) or len(summary.get('boxscore', {}).get('teams', [])) != 2
            if missing_team_box and len(set(expected) & known) == 1:
                score_only.append({'id': gid, 'scores': expected, 'reason': 'Non-D1 final; official box score unavailable', 'source': 'https://www.espn.com/mens-college-basketball/game/_/gameId/' + gid})
                return gid, saved
            complete = cloned(dashboard.completed, get=lambda _: summary, players_box=lambda _: [])
            game = complete(event)
            for tid, box in game['teams'].items():
                if box['points'] != expected[str(tid)] or any(box.get(k) is None for k in ('fga', 'oreb', 'tov', 'fta')):
                    raise ValueError('Incomplete official team box')
            if saved:
                game['observed_complete_at'] = saved['observed_complete_at']
            write(path, {**{k: summary[k] for k in ('header', 'boxscore', 'pickcenter') if k in summary}, '_verified_at': datetime.now(timezone.utc).isoformat()})
            return gid, game
        except Exception as exc:
            pending.append({'id': gid, 'error': str(exc)})
            return gid, games.get(gid)
    with ThreadPoolExecutor(6) as pool:
        for gid, game in pool.map(one, events):
            if game is not None:
                games[gid] = game
    save('boxes', {'games': list(games.values())}, pending=pending, score_only=score_only, results_collected_at=results['collected_at'])
    print(json.dumps({'verified_boxes': len(games), 'pending': len(pending)}))


def collect_players():
    boxes = load('boxes')
    pending = []
    verified = []
    for game in boxes['payload']['games']:
        gid = str(game['id'])
        path = chunk('players', gid)
        try:
            raw = chunk('boxes', gid)
            if raw.exists():
                rows = read(raw).get('boxscore', {}).get('players', [])
                players = {str(r['team']['id']): dashboard.players_box(r) for r in rows}
            else:
                players = game.get('players', {})
            if set(players) != set(game['teams']) or any(not players.get(tid) for tid in game['teams']):
                raise ValueError('Player boxes not yet complete')
            write(path, {'players': players, 'date': game['date'], 'points': {i: b['points'] for i, b in game['teams'].items()}})
            verified.append(gid)
        except Exception as exc:
            pending.append({'id': gid, 'error': str(exc)})
            if path.exists():
                verified.append(gid)
    fallback = {}
    score_only_teams = {str(tid) for game in boxes.get('score_only', []) for tid in game.get('scores', {})}
    if pending:
        try:
            league = archives.league(season(), 2, 'byathlete')
            for slug, team in load('results')['payload']['teams'].items():
                regular = team['phases']['regular']
                rows = league.get(team['team_id'], [])
                finals = [g for g in regular['games'] if g['status'] == 'final']
                if team['team_id'] not in score_only_teams and not team['phases']['postseason']['completed_games'] and rows and sum((p.get('stats') or {}).get('points', 0) for p in rows) == sum(g['points'] for g in finals):
                    fallback[team['team_id']] = rows
        except Exception as exc:
            print('League player fallback unavailable:', type(exc).__name__)
    save('players', {'games': verified, 'fallback': fallback}, pending=pending, boxes_collected_at=boxes['collected_at'])
    print(json.dumps({'verified_player_games': len(verified), 'pending': len(pending)}))


def collect_rosters():
    old = load('rosters', required=False)
    previous = (old or {}).get('payload', {}).get('teams', {})
    errors = []
    def one(team):
        tid = str(team['espn_id'])
        prior = previous.get(tid)
        if prior and prior['roster'].get('observed_at') and (datetime.now(timezone.utc) - datetime.fromisoformat(prior['roster']['observed_at'])).total_seconds() < 4 * 3600:
            return tid, prior
        try:
            raw = archives.get(archives.SITE + f'teams/{tid}/roster?season={season()}')
            if raw.get('season', {}).get('year') != season():
                raise ValueError('Wrong roster season')
            roster = cloned(dashboard.roster, get=lambda _: raw)(tid)
            coaches = [(' '.join(str(c.get(k, '')) for k in ('firstName', 'lastName'))).strip() for c in raw.get('coach', [])]
            return tid, dict(roster=roster, coaches=coaches)
        except Exception as exc:
            errors.append({'team': tid, 'error': str(exc)})
            return tid, prior or {'roster': {'team_id': tid, 'players': [], 'observed_at': None, 'source': None}, 'coaches': []}
    with ThreadPoolExecutor(8) as pool:
        teams = dict(pool.map(one, registry()))
    save('rosters', {'teams': teams}, retained=errors)


def project(folder, include_metrics=True, include_players=True, calculate_metrics=False):
    """Copy canonical archives, change only the active season, and reuse enrichment."""
    results = load('results', hours=30)
    year = str(season())
    target = folder / 'data/cbb/teams'
    target.mkdir(parents=True, exist_ok=True)
    for team in registry():
        path = ROOT / 'data/cbb/teams' / (team['slug'] + '.json')
        doc = read(path) if path.exists() else dict(team_id=str(team['espn_id']), slug=team['slug'], seasons={})
        current = doc.setdefault('seasons', {}).setdefault(year, dict(key=year, label=f'{int(year)-1}–{year[2:]}',
                                                team_id=str(team['espn_id']), phases={}, players=[], coaches=[], sources=[]))
        observed = results['payload']['teams'][team['slug']]
        for label, values in observed['phases'].items():
            current.setdefault('phases', {}).setdefault(label, {}).update(copy.deepcopy(values))
        current['collected_at'] = observed['verified_at']
        write(target / path.name, doc)
    boxes = load('boxes', required=False)
    if boxes and include_metrics and calculate_metrics:
        enrichment.enrich(target, [dict(g, players={}) for g in boxes['payload']['games']], int(year))
    elif include_metrics:
        metrics = load('metrics', required=False)
        if metrics:
            for path in target.glob('*.json'):
                doc = read(path)
                for label, fact in metrics['payload']['teams'].get(path.stem, {}).items():
                    record = doc['seasons'][year]['phases'].get(label)
                    finals = {str(g['id']) for g in record.get('games', []) if g['status'] == 'final'} if record else set()
                    if record and set(fact['game_ids']) == finals:
                        record['metrics'] = fact['metrics']
                        record['coverage'] = fact['coverage']
                write(path, doc)
    players = load('players', required=False)
    if boxes and players and include_players:
        projected = folder / 'player-projection'
        projected.mkdir()
        for path in target.glob('*.json'):
            doc = read(path)
            write(projected / path.name, dict(team_id=doc['team_id'], slug=doc['slug'], seasons={year: doc['seasons'][year]}))
        player_games = []
        for game in boxes['payload']['games']:
            path = chunk('players', game['id'])
            if path.exists():
                fact = read(path)
                if fact.get('points') == {i: b['points'] for i, b in game['teams'].items()}:
                    player_games.append(dict(game, players=fact['players']))
        enrichment.enrich(projected, player_games, int(year))
        for path in sorted(target.glob('*.json')):
            doc = read(path)
            tid = str(doc['team_id'])
            finals = {str(g['id']) for p in doc['seasons'][year]['phases'].values() for g in p.get('games', []) if g['status'] == 'final'}
            usable = {str(g['id']) for g in player_games if tid in g['teams']}
            excluded = {str(g['id']) for g in boxes.get('score_only', []) if tid in g.get('scores', {})}
            if finals and (finals - excluded) <= usable:
                doc['seasons'][year]['players'] = read(projected / path.name)['seasons'][year].get('players', [])
                write(path, doc)
            elif tid in players['payload'].get('fallback', {}):
                doc['seasons'][year]['players'] = players['payload']['fallback'][tid]
                write(path, doc)
    rosters = load('rosters', required=False)
    if rosters:
        for path in sorted(target.glob('*.json')):
            doc = read(path)
            item = rosters['payload']['teams'].get(str(doc['team_id']))
            if item and item.get('coaches'):
                doc['seasons'][year]['coaches'] = item['coaches']
                write(path, doc)
    return target


def collect_metrics():
    load('boxes')
    with tempfile.TemporaryDirectory() as directory:
        target = project(Path(directory), include_metrics=True, include_players=False, calculate_metrics=True)
        for path in target.glob('*.json'):
            doc = read(path)
            for phase, label in ((2, 'regular'), (3, 'postseason')):
                record = doc['seasons'][str(season())]['phases'][label]
                finals = [g for g in record['games'] if g['status'] == 'final']
                current = record.get('metrics', {})
                if not finals or (current.get('gamesPlayed') == len(finals) and current.get('points') == sum(g['points'] for g in finals)):
                    continue
                try:
                    raw = archives.get(f'https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/{season()}/types/{phase}/teams/{doc["team_id"]}/statistics')
                    values = {s['name']: s.get('value') for c in raw.get('splits', {}).get('categories', []) for s in c.get('stats', []) if isinstance(s.get('value'), (int, float)) and math.isfinite(s['value'])}
                    if values.get('gamesPlayed') == len(finals) and values.get('points') == sum(g['points'] for g in finals):
                        record.update(metrics=values, coverage='verified_season_statistics')
                except Exception as exc:
                    print('Retaining metrics for', path.stem, label, type(exc).__name__)
            write(path, doc)
        metrics = {p.stem: {label: {'metrics': phase.get('metrics', {}), 'coverage': phase.get('coverage'),
                                  'game_ids': [str(g['id']) for g in phase.get('games', []) if g['status'] == 'final']
                                      if phase.get('metrics', {}).get('gamesPlayed') == phase['completed_games'] and
                                      phase.get('metrics', {}).get('points') == sum(g['points'] for g in phase.get('games', []) if g['status'] == 'final') else []}
                             for label, phase in read(p)['seasons'][str(season())]['phases'].items()} for p in target.glob('*.json')}
    save('metrics', {'teams': metrics}, results_collected_at=load('results')['collected_at'])


def publish_archives():
    with tempfile.TemporaryDirectory() as directory:
        target = project(Path(directory))
        for path in target.glob('*.json'):
            write(ROOT / 'data/cbb/teams' / path.name, read(path))
    import publish_cbb_team_archives as publisher
    publisher.main()
    save('archive-status', {'components': {name: doc['collected_at'] for name in ('results', 'metrics', 'players', 'rosters') if (doc := load(name, required=False))}})


def publish_derived(kind):
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        target = project(folder, include_players=kind != 'ranks', include_metrics=kind != 'leaders')
        if kind == 'ranks':
            import build_cbb_metric_ranks as ranks
            (folder / 'data/sports').mkdir(parents=True)
            shutil.copy(ROOT / 'data/sports/team-registry.json', folder / 'data/sports/team-registry.json')
            with patch.object(ranks, 'ROOT', folder), patch.object(ranks, 'DATA', target), patch.object(ranks, 'OUT', ROOT / 'data/cbb/metric-ranks.json'):
                ranks.main()
        else:
            import publish_cbb_current_season_leaders as leaders
            path = folder / 'data/cbb/division-one-season-leaders.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / 'data/cbb/division-one-season-leaders.json', path)
            with patch.object(leaders, 'ROOT', folder), patch.object(leaders, 'DATA', path):
                leaders.publish()
            write(ROOT / 'data/cbb/division-one-season-leaders.json', read(path))
    save(kind + '-status', {'components': {name: doc['collected_at'] for name in ('results', 'metrics', 'players') if (doc := load(name, required=False))}})


def overlay_markets(data):
    path = ROOT / f'data/cbb/pregame-markets/{season()}.json'
    ledger = read(path).get('games', {}) if path.exists() else {}
    for game in data['games']:
        quote = ledger.get(str(game['id']))
        if not quote:
            continue
        spread = quote.get('home_spread')
        home, away = data['teams'][game['home']], data['teams'][game['away']]
        favored = home if spread is not None and spread <= 0 else away
        value = 0 if spread == 0 else -abs(spread) if spread is not None else None
        label = favored['abbr'] + ' ' + f'{value:g}' if value is not None else None
        game['market'] = dict(spread=label, total=quote.get('total'), provider=quote.get('provider'), observed_at=quote.get('observed_at'))


def verified_market(game, ledger):
    quote = ledger.get(str(game['id']))
    if quote and (quote.get('source_type') == 'archived_provider' or dashboard.stamp(quote['observed_at']) < dashboard.stamp(quote['tipoff'])):
        return dict(home_spread=quote.get('home_spread'), total=quote.get('total'), provider=quote.get('provider'),
                    line_type=quote.get('line_type', 'observed before tipoff'), observed_at=quote['observed_at'], source=quote.get('source'))
    market = game.get('market')
    if market and market.get('observed_at') and dashboard.stamp(market['observed_at']) < dashboard.stamp(game['date']):
        return market
    return None


def assemble():
    results, boxes, players, rosters = (load(name) for name in ('results', 'boxes', 'players', 'rosters'))
    known = {str(t['espn_id']) for t in registry()}
    market_path = ROOT / f'data/cbb/pregame-markets/{season()}.json'
    market_ledger = read(market_path).get('games', {}) if market_path.exists() else {}
    games = []
    for raw in boxes['payload']['games']:
        if set(raw['teams']) <= known:
            game = copy.deepcopy(raw)
            fact = chunk('players', game['id'])
            observed = read(fact) if fact.exists() else {}
            game['players'] = observed.get('players', {}) if observed.get('points') == {i: b['points'] for i, b in game['teams'].items()} else {}
            game['market'] = verified_market(game, market_ledger)
            games.append(game)
    write(ROOT / 'cbb/dashboard/data/completed-games.json', {'schema_version': 1, 'games': games})
    inputs = {'events': results['payload']['events'], 'rosters': {tid: item['roster'] for tid, item in rosters['payload']['teams'].items()}}
    with patch.object(dashboard, 'ROOT', ROOT):
        dashboard.main(offline_inputs=inputs)
    path = ROOT / 'cbb/dashboard/data/dashboard.json'
    data = read(path)
    overlay_markets(data)
    write(path, data)
    cache = ROOT / 'cbb/dashboard/data/completed-games.json'
    write(cache, read(cache))
    save('status', {'completed_games': len(games), 'matchups': len(data['games']),
                   'components': {d['component']: d['collected_at'] for d in (results, boxes, players, rosters)}})


def publish_markets():
    path = ROOT / 'cbb/dashboard/data/dashboard.json'
    data = read(path)
    overlay_markets(data)
    write(path, data)


def strength_inputs():
    load('results', hours=8)
    import collect_cbb_strength_games as collector
    original = collector.get
    def get(endpoint):
        if endpoint.startswith('scoreboard?'):
            day = endpoint.split('dates=')[-1].split('&')[0]
            return read(store() / 'boards' / str(season()) / (day + '.json'))
        if endpoint.startswith('summary?event='):
            return read(chunk('boxes', endpoint.split('=')[-1]))
        return original(endpoint)  # Existing verified non-D1 classification lookup.
    with patch.object(collector, 'get', get), patch.object(sys, 'argv', ['collect_cbb_strength_games.py', '--season', str(season())]):
        collector.main()


def publish_strength():
    """Render the unchanged strength tables against the latest team-metric facts."""
    results, metrics = load('results', hours=8), load('metrics')
    if metrics.get('results_collected_at') != results['collected_at']:
        raise ValueError('Metric inputs have not caught up with the verified results')
    import publish_cbb_strength as publisher
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        project(folder, include_players=False)
        (folder / 'cbb/rankings').mkdir(parents=True)
        shutil.copy(ROOT / 'cbb/rankings/index.html', folder / 'cbb/rankings/index.html')
        for path in [ROOT / 'data/cbb/strength-rankings.json', ROOT / f'data/cbb/strength-games/{season()}.json']:
            destination = folder / path.relative_to(ROOT)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, destination)
        with patch.object(publisher, 'ROOT', folder):
            publisher.publish()
        for relative in ['cbb/rankings/index.html', 'cbb/rankings/offense/index.html', 'cbb/rankings/defense/index.html']:
            (ROOT / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(folder / relative, ROOT / relative)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['results', 'boxes', 'players', 'metrics', 'rosters', 'archives', 'ranks', 'leaders', 'dashboard', 'markets', 'strength-inputs', 'strength-publish'])
    args = p.parse_args()
    handlers = {'results': collect_results, 'boxes': collect_boxes, 'players': collect_players, 'metrics': collect_metrics,
                'rosters': collect_rosters, 'archives': publish_archives, 'ranks': lambda: publish_derived('ranks'),
                'leaders': lambda: publish_derived('leaders'), 'dashboard': assemble, 'markets': publish_markets,
                'strength-inputs': strength_inputs, 'strength-publish': publish_strength}
    handlers[args.operation]()


if __name__ == '__main__':
    main()
