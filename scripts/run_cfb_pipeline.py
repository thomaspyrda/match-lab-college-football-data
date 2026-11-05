#!/usr/bin/env python3
"""Isolated CFB collectors and offline publication, using the existing builders.

Run in the pinned dashboard-source checkout; --store points into the main checkout.
The original collector's calculation blocks execute verbatim. Only orchestration,
provider access, verified-result filtering, and persistence live here.
"""
import argparse
import copy
import hashlib
import importlib
import json
import math
import os
import runpy
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

SOURCE_REVISION = 'ebb7892f2300f67e174e4d57abeb9b18cdf4ee60'
SOURCE_HASH = 'd9b9aee08712c93df8cdf710f6733ec6fc17bc03301fe4252ae51ee9550e8dd2'
BOUNDARY = 'all_upcoming=[]; now=datetime.now(timezone.utc); end=now+timedelta(days=7)'
METRICS = 'from cfb_dashboard.pipeline.disruption import accumulate_boxes, season_metrics'
PLAYERS = '# Cache pass-level opportunity detail for the player cards.'
UPCOMING = '(DATA/"upcoming.json").write_text('
RANKINGS = '# Publish a current-to-date full-FBS strength snapshot.'


def stamp():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')
    temporary.replace(path)


def load(store, component, max_hours=None, required=True):
    path = store / (component + '.json')
    if not path.exists():
        if required:
            raise ValueError(f'Missing verified CFB input: {component}')
        return None
    data = read(path)
    if data.get('schema_version') != 1 or data.get('component') != component:
        raise ValueError(f'Invalid CFB input contract: {component}')
    if data.get('season') != datetime.now(timezone.utc).year:
        if not required:
            return None
        raise ValueError(f'Wrong CFB season: {component}')
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(data['collected_at'])).total_seconds() / 3600
    if age < -0.1 or (max_hours is not None and age > max_hours):
        if not required:
            return None
        raise ValueError(f'Stale CFB input: {component}, age {age:.1f} hours')
    return data


def save(store, component, payload, **metadata):
    write(store / (component + '.json'), dict(schema_version=1, component=component,
          season=datetime.now(timezone.utc).year, collected_at=stamp(),
          source_revision=SOURCE_REVISION, payload=payload, **metadata))


def query_key(path, params):
    return path + '?' + urllib.parse.urlencode(sorted((k, str(v)) for k, v in params.items()))


def request(path, **params):
    url = 'https://api.collegefootballdata.com' + query_key(path, params)
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + os.environ['CFBD_API_KEY'],
                                              'Accept': 'application/json', 'User-Agent': 'BetWise-CFB-Pipeline/1.0'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                rows = json.load(response)
            if not isinstance(rows, list):
                raise ValueError('Expected CFBD list response')
            return rows
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def verified_games(rows):
    """Only provider-confirmed final games may carry scores into a model."""
    out = []
    ids = set()
    for original in rows:
        row = dict(original)
        gid = str(row['id'])
        if gid in ids:
            raise ValueError('Duplicate CFBD game: ' + gid)
        ids.add(gid)
        scores = []
        for field in ('homePoints', 'awayPoints'):
            value = row.get(field)
            try:
                score = float(value) if value is not None and not isinstance(value, bool) else None
            except (ValueError, TypeError, OverflowError):
                score = None
            scores.append(score if score is not None and math.isfinite(score) and score >= 0 else None)
        if row.get('completed') is True and any(value is None for value in scores):
            # Cancelled/unscored provider records must not stop unrelated verified
            # games, and must never enter records or model calculations as finals.
            row['completed'] = False
            row['verification_issue'] = 'provider_complete_without_valid_scores'
            print('::warning::CFBD game ' + gid + ' is marked complete without valid scores; excluded from final results')
        if row.get('completed') is not True:
            row['homePoints'] = row['awayPoints'] = None
        else:
            row['homePoints'], row['awayPoints'] = scores
        out.append(row)
    return out


def split_source(text):
    """Fail closed if the pinned, tested collector changes."""
    if hashlib.sha256((text.rstrip() + '\n').encode()).hexdigest() != SOURCE_HASH:
        raise ValueError('CFB source revision changed; validate component boundaries before publication')
    a, b, c, d, e = (text.index(x) for x in (BOUNDARY, METRICS, PLAYERS, UPCOMING, RANKINGS))
    return dict(common=text[:a], schedule=text[a:b] + text[d:e], results=text[a:b] + text[d:e] + text[e:],
                metrics=text[b:c], players=text[c:d])


def namespace(root, common):
    sys.path.insert(0, str(root))
    ns = {'__file__': str(root / 'refresh_match_lab.py'), '__name__': 'cfb_component'}
    exec(compile(common, ns['__file__'], 'exec'), ns)
    return ns


def restore_results(root, document):
    for filename, payload in document['payload']['files'].items():
        if filename not in {'data/current_rankings.json', 'data/upcoming.json',
                            'data/cfb_dashboard_team_metadata.json',
                            f'data/historical/{document["season"]}.json'}:
            raise ValueError('Unexpected CFB input file: ' + filename)
        write(root / filename, payload)


def cached_lines(root, market, params):
    if market:
        payload = market['payload']
        if 'week' in params:
            key = str(params['week'])
            if key in payload['weeks']:
                return payload['weeks'][key]
        elif int(params.get('year', 0)) == market['season']:
            return payload['season_lines']
    # Historical markets remain frozen when a live quote collector is unavailable.
    path = root / 'data/historical' / (str(params['year']) + '.json')
    rows = read(path).get('games', []) if path.exists() else []
    return [{'id': g['game_id'], 'lines': [dict(spread=g.get('spread'), overUnder=g.get('over_under'),
             homeMoneyline=g.get('home_moneyline'), awayMoneyline=g.get('away_moneyline'), provider=g.get('provider'))]}
            for g in rows if 'week' not in params or int(g.get('week') or 0) == int(params['week'])]


def historical_games(root, year):
    """Use the frozen archive for prior seasons, rather than re-querying old games."""
    path = root / f'data/historical/{year}.json'
    if not path.exists():
        raise ValueError('Missing frozen CFB historical season: ' + str(year))
    out = []
    for g in read(path)['games']:
        result = g.get('result') or {}
        out.append(dict(id=g['game_id'], season=year, week=g.get('week'),
            homeTeam=g.get('home'), awayTeam=g.get('away'), startDate=g.get('start_date'),
            homePoints=result.get('home_points'), awayPoints=result.get('away_points'), completed=bool(result),
            homeId=g.get('home_id'), awayId=g.get('away_id'), homeConference=g.get('home_conference'),
            awayConference=g.get('away_conference'), conferenceGame=g.get('conference_game'),
            neutralSite=g.get('neutral_site'), venue=g.get('venue'), venueId=g.get('venue_id')))
    return out


def collect_results(root, store, parts):
    ns = namespace(root, parts['common'])
    provider = ns['api']
    market = load(store, 'markets', required=False)
    responses = {}
    year = datetime.now(timezone.utc).year

    def api(path, **params):
        if path == '/lines':
            return copy.deepcopy(cached_lines(root, market, params))
        if path == '/games' and int(params.get('year', 0)) < year:
            return historical_games(root, int(params['year']))
        if path == '/rankings':
            try:
                rows = provider(path, **params)
            except Exception:
                previous = load(store, 'results', required=False)
                rows = (previous or {}).get('payload', {}).get('responses', {}).get(query_key(path, params), [])
                print('AP reference feed unavailable; retaining previous reference when available')
        else:
            rows = provider(path, **params)
        if path == '/games':
            rows = verified_games(rows)
            if int(params.get('year', 0)) == year:
                responses[query_key(path, params)] = copy.deepcopy(rows)
        elif path in ('/teams/fbs', '/rankings') and int(params.get('year', 0)) == year:
            responses[query_key(path, params)] = copy.deepcopy(rows)
        return rows

    ns['api'] = api
    exec(compile(parts['schedule'], str(root / 'refresh_match_lab.py'), 'exec'), ns)
    # This seed is private input state. The independent strength stage runs the
    # original calculations and promotion before any strength can be published.
    seed = read(root / 'data/current_rankings.json')
    seed.update(season=year, week=max(1, ns['last_completed'] + 1))
    write(root / 'data/current_rankings.json', seed)
    # All-season team archives retain postseason results, using their existing schema.
    both = verified_games(provider('/games', year=year, seasonType='both'))
    write(root / '.cfb-result-responses.json', {'responses': responses, 'team_games': both})


def pack_results(root, store):
    year = datetime.now(timezone.utc).year
    files = {p: read(root / p) for p in ['data/current_rankings.json', 'data/upcoming.json',
             'data/cfb_dashboard_team_metadata.json', f'data/historical/{year}.json']}
    history = files[f'data/historical/{year}.json']['games']
    finals = sorted(str(g['game_id']) for g in history if g.get('result'))
    if not finals or len(files['data/cfb_dashboard_team_metadata.json']['teams']) < 130:
        raise ValueError('Incomplete CFB result/ranking source pool')
    raw = read(root / '.cfb-result-responses.json')
    save(store, 'results', dict(files=files, **raw), completed_game_ids=finals,
         through_week=max(int(g.get('week') or 0) for g in history if g.get('result')))


def collect_strength(root, store, parts):
    results = load(store, 'results', max_hours=8)
    restore_results(root, results)
    ns = namespace(root, parts['common'])
    provider = ns['api']
    market = load(store, 'markets', required=False)
    def api(path, **params):
        if path == '/lines':
            return cached_lines(root, market, params)
        if path == '/games' and int(params.get('year', 0)) < results['season']:
            return historical_games(root, int(params['year']))
        if int(params.get('year', 0)) == results['season'] and path in ('/games', '/teams/fbs', '/rankings'):
            key = query_key(path, params)
            if key not in results['payload']['responses']:
                raise ValueError('Verified CFB result snapshot lacks query: ' + key)
            return copy.deepcopy(results['payload']['responses'][key])
        return verified_games(provider(path, **params)) if path == '/games' else provider(path, **params)
    ns['api'] = api
    exec(compile(parts['results'], str(root / 'refresh_match_lab.py'), 'exec'), ns)


def pack_strength(root, store):
    results = load(store, 'results', max_hours=8)
    board = read(root / 'data/current_rankings.json')
    if (board.get('model') or {}).get('version') != 'v15' or len(board.get('teams', [])) < 130:
        raise ValueError('Existing dashboard strength contract was not preserved')
    save(store, 'strength', dict(board=board), through_week=results['through_week'],
         results_collected_at=results['collected_at'])


def stage_namespace(root, store, parts):
    results = load(store, 'results', max_hours=8)
    restore_results(root, results)
    ns = namespace(root, parts['common'])
    ns.update(now=datetime.now(timezone.utc), last_completed=results['through_week'],
              current_records=results['payload']['files'][f'data/historical/{results["season"]}.json']['games'],
              team_meta=read(root / 'data/cfb_dashboard_team_metadata.json')['teams'])
    ns['fbs_teams'] = set(ns['team_meta'])
    failures = []
    provider = ns['api']

    def api(path, **params):
        try:
            return provider(path, **params)
        except Exception:
            failures.append(path)
            raise

    ns['api'] = api
    return ns, results, failures


def availability_reports(store):
    """Read the independent injury job's observations; unlisted players stay unknown."""
    from cfb_dashboard.pipeline.availability import OUT, name_key
    path = store.parents[1] / 'dashboard-availability/cfb.json'
    if not path.exists():
        return {}
    doc = read(path)
    reports = {}
    now = datetime.now(timezone.utc)
    for team_id, team in doc.get('teams', {}).items():
        if team.get('state') != 'reported':
            continue
        date = team.get('report_as_of') or team.get('checked_at')
        try:
            at = datetime.fromisoformat(date.replace('Z', '+00:00'))
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, AttributeError):
            continue
        if not 0 <= (now - at).total_seconds() <= 10 * 86400:
            continue
        for player in team.get('players', []):
            status = str(player.get('status') or '')
            row = dict(status=status, unavailable=status.lower() in OUT,
                       availability_updated=at.isoformat(), availability_note='Reported ' + status)
            reports[(str(team_id), 'name:' + name_key(player.get('name')))] = row
            pid = player.get('id') or player.get('player_id')
            if pid:
                reports[(str(team_id), 'id:' + str(pid).split(':')[-1])] = row
    return reports


def collect_statistics(root, store, component, parts):
    ns, results, failures = stage_namespace(root, store, parts)
    availability = importlib.import_module('cfb_dashboard.pipeline.availability')
    with patch.object(availability, 'fetch_reports', lambda *_: availability_reports(store)):
        exec(compile(parts[component], str(root / 'refresh_match_lab.py'), 'exec'), ns)
    if failures:
        raise ValueError(f'{component} source failed; retain last verified component: {failures}')
    filename = 'cfb_dashboard_raw_metrics.json' if component == 'metrics' else 'cfb_dashboard_player_usage.json'
    payload = {'dashboard': read(root / 'data' / filename)}
    played = {ns['canon_team'](g[side]) for g in ns['current_records'] if g.get('result') for side in ('home', 'away')}
    minimum = min(120, len(played & ns['fbs_teams']))
    if len(payload['dashboard'].get('teams', {})) < minimum:
        raise ValueError('Incomplete CFB ' + component + ' team coverage')
    if component == 'metrics':
        payload['advanced'] = request('/stats/season/advanced', year=results['season'], excludeGarbageTime='true')
        payload['basic'] = request('/stats/season', year=results['season'])
        # Preserve the existing play-mix calculations, independently of dashboard publication.
        path = store.parents[2] / 'refresh_cfb_play_rates.py'
        mod = runpy.run_path(str(path))
        games = results['payload']['files']['data/upcoming.json']['games']
        projection = {'games': [dict(game_id=g['game_id'], season=g['season'], week=g['week'],
                         away={'name': g['away']}, home={'name': g['home']}, matchup_metrics=[]) for g in games]}
        payload['play_mix'] = mod['enrich'](projection)
    else:
        payload['team_players'] = request('/stats/player/season', year=results['season'], seasonType='both')
    save(store, component, payload, through_week=results['through_week'], results_collected_at=results['collected_at'])


def collect_markets(root, store):
    year = datetime.now(timezone.utc).year
    results = load(store, 'results', required=False)
    weeks = set()
    if results:
        weeks = {int(g['week']) for g in results['payload']['files']['data/upcoming.json']['games']}
    payload = dict(season_lines=request('/lines', year=year, seasonType='both'),
                   weeks={str(w): request('/lines', year=year, seasonType='regular', week=w) for w in sorted(weeks)})
    if not payload['season_lines'] and not any(payload['weeks'].values()):
        raise ValueError('Empty CFB markets response; retain last verified quotes')
    save(store, 'markets', payload)


def collect_metadata(store):
    year = datetime.now(timezone.utc).year
    coaches = request('/coaches', year=year)
    recruiting = request('/recruiting/teams', year=year)
    if len(coaches) < 100:
        raise ValueError('Incomplete CFB coaching metadata; retain prior observations')
    save(store, 'metadata', dict(coaches=coaches, recruiting=recruiting))


def collect_context(root, store):
    results = load(store, 'results', max_hours=8)
    restore_results(root, results)
    runpy.run_path(str(root / 'cfb_dashboard/pipeline/refresh_venues.py'), run_name='__main__')
    from cfb_dashboard.pipeline.weather import game_weather
    venues = read(root / 'data/cfb_dashboard_venues.json')
    forecasts = {}
    for g in results['payload']['files']['data/upcoming.json']['games']:
        venue = venues['venues'].get(str(g.get('venue_id'))) or venues['venues'].get(str(g.get('venue'))) or {}
        kickoff = datetime.fromisoformat(g['start_date'].replace('Z', '+00:00'))
        forecasts[str(g['game_id'])] = game_weather(venue, kickoff, bool(g.get('neutral_site')))
    save(store, 'context', dict(venues=venues, forecasts=forecasts))


def apply_markets(payload, market):
    if not market:
        return
    def choose(entry):
        lines = entry.get('lines') or []
        return next((x for x in lines if str(x.get('provider', '')).lower() == 'consensus'),
                    next((x for x in lines if x.get('spread') is not None or x.get('overUnder') is not None), {}))
    quotes = {str(g['id']): choose(g) for g in market['payload']['season_lines']}
    for rows in market['payload']['weeks'].values():
        quotes.update({str(g['id']): choose(g) for g in rows})
    for g in payload['games']:
        line = quotes.get(str(g['game_id']))
        line = line or {}
        g['market'] = dict(spread=line.get('spread'), total=line.get('overUnder'),
                           home_moneyline=line.get('homeMoneyline'), away_moneyline=line.get('awayMoneyline'),
                           provider=line.get('provider'), observed_at=market['collected_at'] if line else None)


def assemble(root, store):
    results = load(store, 'results', max_hours=30)
    strength = load(store, 'strength')
    metrics = load(store, 'metrics')
    players = load(store, 'players')
    context = load(store, 'context', max_hours=48, required=False)
    markets = load(store, 'markets', max_hours=24, required=False)
    restore_results(root, results)
    write(root / 'data/current_rankings.json', strength['payload']['board'])
    write(root / 'data/cfb_dashboard_raw_metrics.json', metrics['payload']['dashboard'])
    write(root / 'data/cfb_dashboard_player_usage.json', players['payload']['dashboard'])
    if context:
        write(root / 'data/cfb_dashboard_venues.json', context['payload']['venues'])
    from cfb_dashboard.pipeline import build_dashboard as builder
    forecasts = context['payload']['forecasts'] if context else {}
    # Assembly is offline: cached forecasts are attached by game ID after the unchanged builder runs.
    with patch.object(builder, 'game_weather', lambda *_: 'Forecast unavailable'):
        builder.main()
    path = root / 'cfb_dashboard/data/dashboard.json'
    # Reuse the current schedule/form/location calculations with verified cached
    # responses, so rest days and By Location use the same completed-game cutoff.
    schedule = runpy.run_path(str(store.parents[2] / 'refresh_cfb_dashboard_schedule_only.py'))['main']
    all_games = {str(g['id']): g for g in results['payload']['team_games'] if g.get('seasonType') == 'regular'}
    for key, rows in results['payload']['responses'].items():
        if key.startswith('/games?'):
            all_games.update({str(g['id']): g for g in rows})
    def schedule_request(route, **params):
        if route == '/teams/fbs':
            return results['payload']['responses'][query_key(route, params)]
        if route == '/games':
            return [g for g in all_games.values() if int(g.get('week') or 0) == int(params['week'])]
        raise ValueError('Uncached schedule request: ' + route)
    with patch.dict(schedule.__globals__, OUT=path, request=schedule_request):
        schedule()
    payload = read(path)
    apply_markets(payload, markets)
    mix = {str(g['game_id']): g for g in metrics['payload']['play_mix']['games']}
    for g in payload['games']:
        if str(g['game_id']) in forecasts:
            g['weather'] = {'summary': forecasts[str(g['game_id'])]}
        extra = mix.get(str(g['game_id']))
        if extra:
            for side in ('away', 'home'):
                g[side].setdefault('raw_metrics', {}).update(extra[side].get('raw_metrics', {}))
            g['matchup_metrics'].extend(extra['matchup_metrics'])
    payload['slate']['play_mix'] = metrics['payload']['play_mix'].get('slate', {}).get('play_mix')
    if not payload['games'] or len({str(g['game_id']) for g in payload['games']}) != len(payload['games']):
        raise ValueError('Empty or duplicate dashboard games')
    # The established launch validator expects its original 11 metrics, before play-mix enrichment.
    baseline = copy.deepcopy(payload)
    for g in baseline['games']:
        g['matchup_metrics'] = g['matchup_metrics'][:11]
    write(path, baseline)
    runpy.run_path(str(root / 'cfb_dashboard/pipeline/validate_launch.py'), run_name='__main__')
    enrich_yardage = runpy.run_path(str(store.parents[2] / 'scripts/cfb_dashboard_yardage.py'))['enrich']
    payload = enrich_yardage(payload, metrics)
    write(path, payload)
    health = {key: {'collected_at': d['collected_at'], 'through_week': d.get('through_week')}
              for key, d in dict(results=results, strength=strength, metrics=metrics, players=players, markets=markets, context=context).items() if d}
    write(store / 'status.json', dict(checked_at=stamp(), components=health, game_count=len(payload['games'])))


def ranking_inputs(root, store):
    results = load(store, 'results', max_hours=8)
    text = (root / 'refresh_match_lab.py').read_text()
    common, remainder = text.split(BOUNDARY, 1)
    ns = namespace(root, common)
    provider = ns['api']
    market = load(store, 'markets', required=False)
    def api(path, **params):
        if path == '/lines':
            return cached_lines(root, market, params)
        if path == '/games' and int(params.get('year', 0)) < results['season']:
            return historical_games(root, int(params['year']))
        if path == '/games' and int(params.get('year', 0)) == results['season']:
            key = query_key(path, params)
            if key not in results['payload']['responses']:
                raise ValueError('Verified CFB result snapshot lacks query: ' + key)
            return copy.deepcopy(results['payload']['responses'][key])
        return verified_games(provider(path, **params)) if path == '/games' else provider(path, **params)
    ns['api'] = api
    exec(compile(BOUNDARY + remainder, str(root / 'refresh_match_lab.py'), 'exec'), ns)


def publish_markets(root, store):
    """Quote publication has no dependency on result, metric, or player collectors."""
    markets = load(store, 'markets', max_hours=24)
    path = root / 'cfb-dashboard-preview/data/dashboard.json'
    payload = read(path)
    apply_markets(payload, markets)
    payload.setdefault('slate', {})['market_generated_at'] = markets['collected_at']
    write(path, payload)


def team_pages(root, store):
    """Refresh active-season page inputs offline; frozen archives and metadata stay intact."""
    from collections import defaultdict
    from refresh_cfb_team_details import canon, num, metric_pairs, player_leaders
    results = load(store, 'results', max_hours=30)
    metrics = load(store, 'metrics')
    players = load(store, 'players')
    markets = load(store, 'markets', required=False)
    metadata = load(store, 'metadata', max_hours=168, required=False)
    year = results['season']
    target = root / f'data/cfb/details/{year}.json'
    previous = read(target) if target.exists() else dict(year=year, sources=[], teams={})
    fbs = set(previous['teams']) | {canon(t) for t in results['payload']['files']['data/cfb_dashboard_team_metadata.json']['teams']}
    for team in fbs:
        previous['teams'].setdefault(team, dict(coaches=[], recruiting=None))
    if metadata:
        coaches = defaultdict(list)
        for coach in metadata['payload']['coaches']:
            name = (coach.get('firstName', '') + ' ' + coach.get('lastName', '')).strip()
            for season in coach.get('seasons') or []:
                if str(season.get('year')) == str(year):
                    coaches[canon(season['school'])].append(dict(name=name, games=season.get('games'),
                        wins=season.get('wins'), losses=season.get('losses'), ties=season.get('ties'), final_ap_rank=season.get('postseasonRank')))
        recruiting = {canon(r['team']): {'rank': r.get('rank'), 'points': r.get('points')} for r in metadata['payload']['recruiting']}
        for team, detail in previous['teams'].items():
            if team in coaches:
                detail['coaches'] = coaches[team]
            if team in recruiting:
                detail['recruiting'] = recruiting[team]
    basic = defaultdict(dict)
    for r in metrics['payload']['basic']:
        value = num(r.get('statValue'))
        if value is not None:
            basic[canon(r['team'])][r['statName']] = value
    advanced = {canon(r['team']): r for r in metrics['payload']['advanced']}
    leaders = player_leaders(players['payload']['team_players'], fbs)
    lines = cached_lines(root, markets, {'year': year})
    def choose(rows):
        return next((r for r in rows if str(r.get('provider', '')).lower() == 'consensus'),
                    next((r for r in rows if r.get('spread') is not None or r.get('overUnder') is not None), {}))
    quotes = {str(r['id']): choose(r.get('lines') or []) for r in lines}
    for rows in (markets or {}).get('payload', {}).get('weeks', {}).values():
        quotes.update({str(r['id']): choose(r.get('lines') or []) for r in rows})
    games = []
    played = defaultdict(int)
    for g in results['payload']['team_games']:
        if canon(g.get('homeTeam')) not in fbs and canon(g.get('awayTeam')) not in fbs:
            continue
        line = quotes.get(str(g['id']), {})
        final = {'home_points': g['homePoints'], 'away_points': g['awayPoints']} if g.get('completed') is True else None
        games.append(dict(game_id=str(g['id']), season=year, week=g.get('week'), start_date=g.get('startDate'),
            season_type=g.get('seasonType') or 'regular', notes=g.get('notes') or '',
            home=g.get('homeTeam'), away=g.get('awayTeam'), home_id=g.get('homeId'), away_id=g.get('awayId'),
            home_conference=g.get('homeConference'), away_conference=g.get('awayConference'),
            neutral_site=g.get('neutralSite'), conference_game=g.get('conferenceGame'),
            home_profile={'classification': 'FBS' if canon(g.get('homeTeam')) in fbs else 'FCS/Other'},
            away_profile={'classification': 'FBS' if canon(g.get('awayTeam')) in fbs else 'FCS/Other'},
            spread=line.get('spread'), over_under=line.get('overUnder'), provider=line.get('provider'), result=final))
        if final:
            played[canon(g['homeTeam'])] += 1
            played[canon(g['awayTeam'])] += 1
    for team, detail in previous['teams'].items():
        pairs = metric_pairs(advanced.get(team, {}), basic.get(team, {}))
        for pair in pairs:
            if pair['label'] in ['Total yards', 'Passing yards', 'Rushing yards'] and played[team] > 0:
                pair['label'] += ' per game'
                for side in ['offense', 'defense']:
                    if pair[side] is not None:
                        pair[side] /= played[team]
        detail.update(metrics=pairs, basic_totals=basic.get(team, {}), leaders=leaders.get(team, {}))
    previous.update(games=games, updated_at=stamp(), basic_stats_collected=True, basic_stats_version=2,
                    leader_schema_version=2,
                    player_stat_catalog=sorted({str(r.get('category')) + ':' + str(r.get('statType'))
                                                for r in players['payload']['team_players']}),
                    team_stat_catalog=sorted({r['statName'] for r in metrics['payload']['basic']}))
    write(target, previous)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=['collect-results', 'pack-results', 'collect-strength', 'pack-strength', 'collect-metrics', 'collect-players',
                   'collect-markets', 'collect-context', 'collect-metadata', 'assemble', 'ranking-inputs', 'require-results', 'team-pages', 'publish-markets'])
    p.add_argument('--store', type=Path, required=True)
    args = p.parse_args(argv)
    root, store = Path.cwd(), args.store.resolve()
    sys.path.insert(0, str(root))
    store.mkdir(parents=True, exist_ok=True)
    if args.operation == 'require-results':
        load(store, 'results', max_hours=8)
    elif args.operation == 'team-pages':
        team_pages(root, store)
    elif args.operation == 'publish-markets':
        publish_markets(root, store)
    elif args.operation == 'ranking-inputs':
        ranking_inputs(root, store)
    elif args.operation == 'collect-markets':
        collect_markets(root, store)
    elif args.operation == 'collect-context':
        collect_context(root, store)
    elif args.operation == 'collect-metadata':
        collect_metadata(store)
    elif args.operation == 'assemble':
        assemble(root, store)
    elif args.operation == 'pack-results':
        pack_results(root, store)
    elif args.operation == 'pack-strength':
        pack_strength(root, store)
    else:
        parts = split_source((root / 'refresh_match_lab.py').read_text())
        if args.operation == 'collect-results':
            collect_results(root, store, parts)
        elif args.operation == 'collect-strength':
            collect_strength(root, store, parts)
        else:
            collect_statistics(root, store, args.operation.removeprefix('collect-'), parts)


if __name__ == '__main__':
    main()
