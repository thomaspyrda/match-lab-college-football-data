#!/usr/bin/env python3
"""Build current NBA regular-season player leaders from completed ESPN boxes."""
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
STATS = ('points', 'rebounds', 'assists', 'steals', 'blocks', 'tpm', 'fgm',
         'ftm', 'turnovers', 'minutes', 'fga', 'tpa', 'fta')
COUNTING = [('points', 'Points'), ('rebounds', 'Rebounds'), ('assists', 'Assists'),
            ('steals', 'Steals'), ('blocks', 'Blocks'), ('tpm', 'Three-Pointers Made'),
            ('fgm', 'Field Goals Made'), ('ftm', 'Free Throws Made'),
            ('turnovers', 'Turnovers'), ('minutes', 'Minutes')]


def build_leaders(cache, teams, season, now):
    def stamp(v):
        return datetime.fromisoformat(v.replace('Z', '+00:00'))
    games = [g for g in cache['games'] if g['season'] == season and g['phase'] == 2
             and stamp(g['observed_complete_at']) <= now and stamp(g['date']) <= now]
    # Never count a game or player appearance twice.
    if len({g['id'] for g in games}) != len(games):
        raise ValueError('Duplicate completed game IDs')
    team_games = Counter(tid for g in games for tid in g['teams'])
    max_games = max(team_games.values(), default=0)
    min_games = max(1, math.ceil(.7 * max_games))
    players = {}
    seen = set()
    for g in sorted(games, key=lambda g: (g['date'], g['id'])):
        for tid, rows in g.get('players', {}).items():
            for p in rows:
                if not p.get('minutes') or p['minutes'] <= 0:
                    continue
                key = (g['id'], p['id'])
                if key in seen:
                    raise ValueError('Duplicate player appearance')
                seen.add(key)
                r = players.setdefault(p['id'], dict(id=p['id'], name=p['name'], games=0,
                    team_ids=[], totals=defaultdict(float), coverage=Counter()))
                r['name'] = p['name']
                r['games'] += 1
                if tid not in r['team_ids']:
                    r['team_ids'].append(tid)
                for stat in STATS:
                    value = p.get(stat)
                    if value is not None and math.isfinite(value):
                        r['totals'][stat] += value
                        r['coverage'][stat] += 1
                box = [p.get(k) for k in ('points', 'rebounds', 'assists', 'steals', 'blocks')]
                if all(v is not None for v in box):
                    tens = sum(v >= 10 for v in box)
                    for stat, threshold in [('double_doubles', 2), ('triple_doubles', 3)]:
                        r['totals'][stat] += tens >= threshold
                        r['coverage'][stat] += 1
    for r in players.values():
        r['totals'] = {k: v for k, v in r['totals'].items() if r['coverage'][k] == r['games']}
        r['teams'] = [dict(id=tid, name=teams[tid]['name'],
                           abbreviation=teams[tid]['abbreviation'], slug=teams[tid].get('slug'))
                      for tid in r.pop('team_ids')]
        del r['coverage']

    def total(r, key):
        return r['totals'].get(key)

    def ratio(r, numerator, denominator, scale=100):
        t = r['totals']
        keys = set(numerator) | set(denominator)
        if not keys <= t.keys():
            return None
        den = sum(t[k] * v for k, v in denominator.items())
        return sum(t[k] * v for k, v in numerator.items()) / den * scale if den > 0 else None

    groups = [dict(id='totals', label='Season Totals', tables=[]),
              dict(id='averages', label='Averages per Game', tables=[]),
              dict(id='efficiency', label='Efficiency', tables=[])]

    def table(group, key, label, unit, value, qualifies=lambda r: True, note=''):
        rows = []
        for r in players.values():
            if not qualifies(r):
                continue
            v = value(r)
            if v is not None and math.isfinite(v):
                rows.append(dict(id=r['id'], name=r['name'], teams=r['teams'], games=r['games'], value=v))
        rows.sort(key=lambda r: (-r['value'], r['name'], r['id']))
        previous = None
        for i, r in enumerate(rows):
            r['rank'] = i + 1 if r['value'] != previous else rows[i-1]['rank']
            previous = r['value']
        groups[group]['tables'].append(dict(key=key, label=label, unit=unit,
            qualification=note, eligible_players=len(rows), rows=rows[:10]))

    for key, label in COUNTING:
        table(0, key, label, 'minutes' if key == 'minutes' else 'total', lambda r, k=key: total(r, k))
        table(1, key + '_per_game', label + ' / Game', 'average',
              lambda r, k=key: total(r, k) / r['games'] if total(r, k) is not None else None,
              lambda r: r['games'] >= min_games,
              f'Minimum {min_games} recorded appearance(s): 70% of the most games played by any team, rounded up.')
    for key, label in [('double_doubles', 'Double-Doubles'), ('triple_doubles', 'Triple-Doubles')]:
        table(0, key, label, 'total', lambda r, k=key: total(r, k),
              lambda r, k=key: (total(r, k) or 0) > 0,
              'At least one recorded. A double-double has 10+ in two of points, rebounds, assists, steals and blocks; a triple-double has three.')
    # These are transparent site qualifications, not official NBA eligibility rules.
    for key, label, made, attempts, minimum in [
            ('fg_pct', 'Field-Goal Percentage', 'fgm', 'fga', 10),
            ('three_pct', 'Three-Point Percentage', 'tpm', 'tpa', 5),
            ('ft_pct', 'Free-Throw Percentage', 'ftm', 'fta', 5)]:
        threshold = minimum * max(max_games, 1)
        table(2, key, label, 'percent', lambda r, m=made, a=attempts: ratio(r, {m: 1}, {a: 1}),
              lambda r, a=attempts, n=threshold: r['games'] >= min_games and (total(r, a) or 0) >= n,
              f'Minimum {min_games} appearance(s) and {threshold} attempts ({minimum} × league team-game benchmark).')
    threshold = 10 * max(max_games, 1)
    for key, label, numerator, denominator in [
            ('efg_pct', 'Effective FG%', {'fgm': 1, 'tpm': .5}, {'fga': 1}),
            ('ts_pct', 'True Shooting%', {'points': 1}, {'fga': 2, 'fta': .88})]:
        table(2, key, label, 'percent', lambda r, n=numerator, d=denominator: ratio(r, n, d),
              lambda r: r['games'] >= min_games and (total(r, 'fga') or 0) >= threshold,
              f'Minimum {min_games} appearance(s) and {threshold} field-goal attempts. '
              + ('(FGM + 0.5 × 3PM) / FGA.' if key == 'efg_pct' else 'PTS / [2 × (FGA + 0.44 × FTA)].'))
    table(2, 'assist_turnover_ratio', 'Assist / Turnover Ratio', 'ratio',
          lambda r: ratio(r, {'assists': 1}, {'turnovers': 1}, 1),
          lambda r: r['games'] >= min_games and (total(r, 'assists') or 0) >= 3 * max(max_games, 1),
          f'Minimum {min_games} appearance(s), {3 * max(max_games, 1)} assists and one turnover. Zero-turnover ratios are undefined.')
    return dict(season=season, label=f'{season-1}–{str(season)[2:]}', phase='Regular season',
                updated_at=now.isoformat(), completed_games=len(games), players=len(players),
                max_team_games=max_games, groups=groups,
                source='https://www.espn.com/nba/scoreboard')


def render_page(data, base):
    e = escape
    def fmt(v, unit):
        if unit == 'total':
            return f'{v:,.0f}'
        if unit == 'ratio':
            return f'{v:.2f}'
        return f'{v:,.1f}' + ('%' if unit == 'percent' else '')
    def row(r, unit):
        athlete = r['id'].split(':')[-1]
        player = (f'<a href="https://www.espn.com/nba/player/_/id/{athlete}">{e(r["name"])}</a>'
                  if athlete.isdigit() else e(r['name']))
        teams = ' / '.join(f'<span title="{e(t["name"], quote=True)}">{e(t["abbreviation"])}</span>' for t in r['teams'])
        return f'<tr><td>{r["rank"]}</td><td>{player}</td><td>{teams}</td><td>{r["games"]}</td><td>{fmt(r["value"],unit)}</td></tr>'
    def table(t):
        rows = ''.join(row(r,t['unit']) for r in t['rows'])
        if not rows:
            rows = '<tr><td colspan="5">No qualifying players yet.</td></tr>'
        value_label = {'total':'Total', 'minutes':'Total', 'average':'Average', 'percent':'Percent', 'ratio':'Ratio'}[t['unit']]
        return f'<section class="leaderboard-section"><h3>{e(t["label"])}</h3><p class="leader-qualification">{e(t["qualification"])}</p><div class="leaderboard-table-wrap"><table class="data-table"><caption class="sr-only">Top 10 NBA {e(t["label"])}</caption><thead><tr><th scope="col">Rank</th><th scope="col">Player</th><th scope="col">Team</th><th scope="col">GP</th><th scope="col">{value_label}</th></tr></thead><tbody>{rows}</tbody></table></div></section>'
    date = datetime.fromisoformat(data['updated_at']).astimezone(ZoneInfo('America/New_York')).strftime('%b %-d, %Y · %-I:%M %p ET')
    body = f'<p class="eyebrow">BETWISE NBA · SEASON LEADERS</p><h1>{e(data["label"])} NBA Season Leaders</h1><p class="page-intro">Top 10 players in season totals, averages per game and shooting efficiency. Completed regular-season games only.</p><p class="page-intro">Updated {date} · {data["completed_games"]} completed games · {data["players"]} players with recorded appearances.</p>'
    body += '<div class="rank-hero"><img src="https://matchlab.parlaycalculator.bet/nba/dashboard/hero-new.png?v=nba-giannis7-20261016" alt="NBA players featured on the BetWise NBA Dashboard"></div><p class="rank-tabs-label">Explore NBA Rankings</p><nav class="rank-tabs" aria-label="NBA rankings"><a href="/nba/rankings/">Overall Team Rankings</a><a href="/nba/offensive-rankings/">Offensive Rankings</a><a href="/nba/defensive-rankings/">Defensive Rankings</a><a href="/nba/season-leaders/" class="active" aria-current="page">Season Leaders</a></nav>'
    body += '<p class="page-intro leader-note">GP counts recorded appearances with minutes played; DNPs are excluded. Early-season samples are small. Each table shows up to 10 qualifying players; ties share a rank, with names used to order tied players. Turnovers measure volume, not better performance. Traded players combine their appearances across teams. Qualifications below are site rules and are not official NBA eligibility rules.</p><nav class="leader-group-nav" aria-label="Leader statistic groups">' + ''.join(f'<a href="#{g["id"]}">{e(g["label"])}</a>' for g in data['groups']) + '</nav>'
    for g in data['groups']:
        body += f'<section id="{g["id"]}" class="leader-group"><h2>{e(g["label"])}</h2><div class="leaderboard-grid">' + ''.join(table(t) for t in g['tables']) + '</div></section>'
    body += '<p class="nba-rank-source">Source: <a href="https://www.espn.com/nba/scoreboard">ESPN completed regular-season box scores</a>. Updated daily with the NBA dashboard. Missing box-score values are excluded from affected categories. Averages use recorded player appearances; team-game benchmark is the maximum completed games played by any NBA team in this dataset. <a href="/nba/season-leaders/data/leaders.json">Download the data</a>.</p>'
    base = re.sub(r'<title>.*?</title>', '<title>NBA Season Leaders | BetWise</title>', base)
    base = re.sub(r'<meta name="description"[^>]+>', '<meta name="description" content="Top 10 NBA players in points, rebounds, assists, steals, blocks, shooting and more. Updated daily.">', base)
    base = base.replace('rel="canonical" href="https://matchlab.parlaycalculator.bet/nba/rankings/"', 'rel="canonical" href="https://matchlab.parlaycalculator.bet/nba/season-leaders/"')
    base = re.sub(r'<script[^>]+/nba/rankings/rankings\.js[^>]*></script>', '', base)
    base = base.replace('</head>', '<link rel="stylesheet" href="/sports-research/season-leaders.css?v=1"><link rel="stylesheet" href="/nba/season-leaders/leaders.css?v=1"></head>')
    return re.sub(r'<main\b.*?</main>', lambda m: '<main class="nba-rankings-main">' + body + '</main>', base, flags=re.S)


def main():
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo('America/New_York'))
    season = today.year + (today.month >= 7)
    registry = json.loads((ROOT/'data/sports/team-registry.json').read_text())
    teams = {t['espn_id']:t for t in registry['teams'] if t['sport']=='nba'}
    cache = json.loads((ROOT/'nba/dashboard/data/completed-games.json').read_text())
    data = build_leaders(cache, teams, season, now)
    dest = ROOT/'nba/season-leaders'
    (dest/'data').mkdir(parents=True, exist_ok=True)
    (dest/'data/leaders.json').write_text(json.dumps(data, separators=(',', ':'))+'\n')
    (dest/'index.html').write_text(render_page(data, (ROOT/'nba/rankings/index.html').read_text()))
    print(f'NBA {data["label"]} leaders: {data["completed_games"]} completed games, {data["players"]} players, {sum(len(g["tables"]) for g in data["groups"])} top-10 tables')


if __name__ == '__main__':
    main()
