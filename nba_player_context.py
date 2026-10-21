"""Observed NBA availability and validated, league-wide player value snapshots."""
import json
import math
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

API = 'https://site.api.espn.com/apis/site/v2/sports/basketball/nba/'
ET = ZoneInfo('America/New_York')


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def normalize_injury(row):
    athlete = row.get('athlete') or {}
    athlete_id = str(athlete.get('id') or '')
    if not athlete_id.isdigit():
        for link in athlete.get('links', []):
            match = re.search(r'espn\.com/nba/player/(?:[^/]+/)*_/id/(\d+)', link.get('href', ''))
            if match:
                athlete_id = match[1]
                break
    details = row.get('details') or {}
    reason = [details.get(k) for k in ('side', 'type', 'detail')]
    reason = [v for v in reason if v and v.lower() not in ('not specified', 'other')]
    return dict(player_id='nba:espn:player:'+athlete_id if athlete_id.isdigit() else None,
                name=athlete.get('displayName') or athlete.get('fullName') or 'Player not identified',
                position=(athlete.get('position') or {}).get('abbreviation'),
                status=row.get('status') or (row.get('type') or {}).get('description') or 'Not specified',
                reason=' · '.join(reason) or 'Reason not provided',
                reported_at=row.get('date'), expected_return=details.get('returnDate'))


def build_availability(team_id, game_date, now, rows=None, source=None, report_as_of=None, context='matchup'):
    day = stamp(game_date).astimezone(ET).date()
    result = dict(game_date=day.isoformat(), checked_at=now.isoformat(), source=source,
                  report_as_of=report_as_of, context=context, players=[])
    today = now.astimezone(ET).date()
    if day != today:
        result['state'] = 'pending' if day > today else 'expired'
        return result
    if not isinstance(rows,list):
        result['state'] = 'unavailable'
        return result
    if report_as_of:
        try:
            age = now-stamp(report_as_of)
            if age > timedelta(hours=30) or age < -timedelta(minutes=5):
                result['state'] = 'unavailable'
                return result
        except (ValueError, TypeError):
            result['state'] = 'unavailable'
            return result
    result['state'] = 'reported'
    priority = {'out':0, 'doubtful':1, 'questionable':2, 'day-to-day':3, 'probable':4, 'available':5}
    players = [normalize_injury(r) for r in rows]
    # Use source updates observed by this snapshot only.
    players = [p for p in players if not p['reported_at'] or stamp(p['reported_at']) <= now]
    unique = {}
    for p in sorted(players, key=lambda p: p['reported_at'] or ''):
        unique[p['player_id'] or p['name']] = p
    result['players'] = sorted(unique.values(), key=lambda p:(priority.get(p['status'].lower(),6),p['name']))
    return result


def refresh_availability(games, now, fetch):
    """Only fetch matchup reports for today's games; future dates stay pending."""
    today = now.astimezone(ET).date()
    todays = [g for g in games if stamp(g['date']).astimezone(ET).date() == today]
    if not todays:
        for g in games:
            for side in ('away','home'):
                g[side]['availability'] = build_availability(g[side]['id'],g['date'],now)
        return
    fallback = None
    try:
        raw = fetch(API+'injuries?limit=1000')
        expected_season = today.year+(today.month>=7)
        if (raw.get('status') == 'success' and isinstance(raw.get('injuries'),list)
                and raw.get('season',{}).get('year') == expected_season and raw.get('timestamp')):
            fallback = raw
    except Exception:
        pass
    fallback_groups = {str(t['id']):t.get('injuries',[]) for t in fallback['injuries']} if fallback else {}

    def report(g):
        try:
            raw = fetch(API+'summary?event='+str(g['id']))
            if str((raw.get('header') or {}).get('id')) != str(g['id']):
                return g['id'],None
            groups = raw.get('injuries')
            if not isinstance(groups,list):
                return g['id'],None
            return g['id'],{str(t.get('team',{}).get('id')):t.get('injuries',[]) for t in groups}
        except Exception:
            return g['id'],None
    reports = dict(ThreadPoolExecutor(max_workers=6).map(report,todays))
    for g in games:
        groups = reports.get(g['id'])
        for side in ('away','home'):
            team = g[side]
            tid = str(team['id'])
            if groups is not None and tid in groups:
                rows,source,as_of,context = groups[tid],g['source'],now.isoformat(),'matchup'
            elif fallback:
                rows,source,as_of,context = fallback_groups.get(tid,[]),'https://www.espn.com/nba/injuries',fallback.get('timestamp'),'team_report'
            else:
                rows,source,as_of,context = None,g['source'],None,'matchup'
            team['availability'] = build_availability(tid,g['date'],now,rows,source,as_of,context)


def player_values(snapshot, season, phase, cutoff, expected_ids=()):
    """Percentiles require a complete same-season league export, never a team subset."""
    if snapshot.get('season') != season or snapshot.get('season_type') != phase:
        raise ValueError('Player value snapshot has a different season or season type')
    as_of = stamp(snapshot['as_of'])
    if as_of > cutoff or cutoff-as_of > timedelta(days=3):
        raise ValueError('Player value snapshot is future-dated or stale')
    if snapshot.get('coverage') != 'league' or not str(snapshot.get('source','')).startswith('https://'):
        raise ValueError('Player value snapshot must identify a complete league source')
    players = {}
    for row in snapshot['players']:
        pid = row['id']
        if not re.fullmatch(r'nba:espn:player:\d+',pid) or pid in players:
            raise ValueError('Player values require unique, verified ESPN player IDs')
        if row.get('games',0) <= 0:
            continue
        value = row.get('vorp')
        if not isinstance(value,(float,int)) or not math.isfinite(value):
            raise ValueError('Missing VORP in the league population')
        bpm = row.get('bpm')
        if bpm is not None and (not isinstance(bpm,(float,int)) or not math.isfinite(bpm)):
            raise ValueError('Invalid BPM')
        players[pid] = dict(vorp=value,bpm=bpm)
    if not set(expected_ids) <= players.keys():
        raise ValueError('Player value export is missing observed NBA players')
    values = [p['vorp'] for p in players.values()]
    n = len(values)
    for p in players.values():
        less = sum(v < p['vorp'] for v in values)
        equal = sum(v == p['vorp'] for v in values)
        p['vorp_percentile'] = round(100*(less+(equal-1)/2)/(n-1),1) if n>1 else None
    return players,dict(state='available',source=snapshot['source'],as_of=snapshot['as_of'],
                        population=n,percentile_method='League rank percentile; ties receive their average rank; players with zero appearances are excluded.')


def load_player_values(path, season, phase, cutoff, expected_ids=()):
    try:
        return player_values(json.loads(Path(path).read_text()),season,phase,cutoff,expected_ids)
    except (OSError,ValueError,KeyError,TypeError):
        return {},dict(state='unavailable',source=None,as_of=None,population=0)
