#!/usr/bin/env python3
"""Build team directories and extensible season research pages from verified IDs.

Team identity is stable; affiliation/name at game time belongs to season data.
Missing season files are uncollected, never zero records or inferred inactivity.
"""
from __future__ import annotations
import html
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = 'https://matchlab.parlaycalculator.bet'
SPORTS = {
    'mlb': {'label': 'MLB', 'name': 'Major League Baseball', 'guide': 'mlb-betting-research-guide', 'features': [('Results & splits', 'Season records, home and road performance, and game-by-game results.'), ('Team & pitching metrics', 'Run production, pitching performance, starters, and bullpen context.'), ('Market history', 'Moneylines, run lines, totals, and closing-line results when verified sources are available.')]},
    'nba': {'label': 'NBA', 'name': 'NBA basketball', 'guide': 'nba-betting-research-guide', 'features': [('Results & splits', 'Season records, home and road performance, and game-by-game results.'), ('Team efficiency', 'Offensive and defensive ratings, pace, shooting, and possession-based metrics.'), ('Market history', 'Spreads, totals, and closing-line results when verified sources are available.')]},
    'cbb': {'label': 'CBB', 'name': "Division I men's college basketball", 'guide': 'college-basketball-betting-research-guide', 'features': [('Results & splits', 'Season records, conference games, home and road performance, and game-by-game results.'), ('Team efficiency', 'Possession-based offense and defense, pace, shooting, and opponent-adjusted context.'), ('Market history', 'Spreads, totals, and closing-line results when verified sources are available.')]},
}

def esc(value):
    return html.escape(str(value), quote=True)

def slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')

def seasons(sport):
    now = datetime.now(timezone.utc)
    # Basketball uses the ending year, preserving the provider season convention.
    last = now.year if sport == 'mlb' else now.year + (now.month >= 7)
    first = 2015 if sport == 'mlb' else 2016
    return [(str(y), str(y) if sport == 'mlb' else f'{y-1}–{str(y)[2:]}') for y in range(first, last + 1)]

def nav_links():
    return '<a href="https://parlaycalculator.bet/betwise/">Why BetWise?</a><a href="https://nfl.parlaycalculator.bet/">NFL</a><a href="https://matchlab.parlaycalculator.bet/">CFB</a>' + ''.join(f'<a href="{BASE}/{s}/teams/">{info["label"]}</a>' for s, info in SPORTS.items()) + '<a href="https://parlaycalculator.bet/#calculator">Parlay Calculator</a><a href="https://parlaycalculator.bet/resources/">All Resources</a>'

def shell(title, description, path, body, indexable=True):
    links = nav_links()
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | BetWise</title><meta name="description" content="{esc(description)}"><meta name="robots" content="{'index' if indexable else 'noindex'},follow"><link rel="canonical" href="{BASE}{path}">
<link rel="icon" href="{BASE}/assets/betwise-logo.png"><link rel="stylesheet" href="{BASE}/cfb-dashboard-preview/styles.css?v=27"><link rel="stylesheet" href="{BASE}/site-navigation.css?v=2"><link rel="stylesheet" href="{BASE}/sports-research/team-research.css?v=1">
<script src="{BASE}/site-navigation-v3.js" defer></script><script src="{BASE}/sports-research/team-research.js?v=1" defer></script><script id="team-color-script" src="https://matchlab.parlaycalculator.bet/sports-research/team-theme.js?v=2" defer></script><style id="team-section-title-style">.team-section:not(#snapshot) .team-section-head h2{{display:none!important}}</style></head><body>
<header class="site-header"><div class="header-inner"><a class="betwise-brand" href="https://parlaycalculator.bet/" aria-label="BetWise and ParlayCalculator.bet home"><img src="{BASE}/assets/betwise-logo.png" alt="BetWise Sports Picks" width="60" height="60"></a><nav class="site-nav" aria-label="Primary navigation">{links}</nav><details class="mobile-menu"><summary aria-label="Open navigation menu">Menu</summary><nav aria-label="Mobile navigation">{links}</nav></details></div></header>
<main class="research-main">{body}</main><footer class="research-footer">BetWise team research · <a href="https://parlaycalculator.bet/resources/">All Resources</a></footer></body></html>'''

def write(path, title, description, body, indexable=True):
    dest = ROOT / path.lstrip('/') / 'index.html'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(shell(title, description, path, body, indexable), encoding='utf-8')

def card(team, group):
    name = ' '.join([team['name'], *team['aliases']]).lower()
    return f'''<a class="conference-team" href="{BASE}/{team['sport']}/teams/{team['slug']}/" data-team-name="{esc(name)}" data-group="{esc(group)}"><img src="{esc(team['logo'])}" alt="" loading="lazy" width="48" height="48"><div><strong>{esc(team['name'])}</strong><small>Team history &amp; season archive</small></div></a>'''

def directory(sport, teams, checked):
    info = SPORTS[sport]; grouped = defaultdict(list)
    for team in teams:
        grouped[(team['conference'] if sport != 'cbb' else '', team['division'] or team['conference'])].append(team)
    options = '<option value="">All divisions</option>' if sport != 'cbb' else '<option value="">All conferences</option>'
    jumps = ''; sections = ''; previous = None
    for (parent, group), rows in sorted(grouped.items()):
        key = slug(parent + ' ' + group)
        label = group if sport != 'nba' else parent.replace(' Conference', '') + ' · ' + group
        options += f'<option value="{esc(key)}">{esc(label)}</option>'
        jumps += f'<a href="#{key}">{esc(label)}</a>'
        if parent != previous:
            if previous is not None: sections += '</div>'
            sections += f'<div class="league-section">{f"<h2 class=\"league-heading\">{esc(parent)}</h2>" if parent else ""}'
            previous = parent
        sections += f'<section class="conference-group" id="{key}"><h2>{esc(group)} <small>{len(rows)} teams</small></h2><div class="conference-teams">' + ''.join(card(t,key) for t in sorted(rows,key=lambda t:t['name'])) + '</div></section>'
    sections += '</div>'
    group_name = 'conference' if sport == 'cbb' else 'division'
    jump_nav = '' if sport == 'cbb' else f'<nav class="directory-jumps" aria-label="Jump to {group_name}">{jumps}</nav>'
    body = f'''<section class="research-intro"><p class="research-kicker">BetWise · {info['label']} teams</p><h1>Explore {"college basketball" if sport == 'cbb' else info['label']}<br>{group_name} by {group_name}.</h1><p>Choose a team to open its season research page. Historical results and statistics will be added gradually, starting with {'2015' if sport == 'mlb' else '2015–16'}.</p><div class="research-meta"><span>{len(teams)} teams</span><span>{len(grouped)} {group_name}s</span><span>{'2026' if sport == 'mlb' else '2026–27'} membership</span></div></section>
<div class="directory-controls"><label for="team-search">Find a team<input id="team-search" type="search" placeholder="Search team name or abbreviation" autocomplete="off"></label><label for="group-filter">Choose a {group_name}<select id="group-filter">{options}</select></label></div><p class="search-status" id="search-status" role="status" aria-live="polite">{len(teams)} teams shown</p>{jump_nav}<p class="empty-search" id="empty-search" hidden>No teams match your search. Try another name or choose all {group_name}s.</p><div class="conference-directory">{sections}</div><p class="research-source">Membership checked {esc(checked[:10])} using ESPN's sport-specific team and conference directories. <a href="https://www.espn.com/{'mens-college-basketball' if sport == 'cbb' else sport}/teams">View source directory</a>.</p>'''
    write(f'/{sport}/teams/', f'{info["label"]} Teams by {group_name.title()}', f'Browse {len(teams)} {info["name"]} teams grouped by {group_name}, with individual team pages and season research archives.', body)

def load_history(team):
    path = ROOT / 'data' / 'sports' / team['sport'] / 'teams' / f'{team["espn_id"]}.json'
    if not path.exists(): return {}
    data = json.loads(path.read_text())
    assert data['schema_version'] == 1 and data['team_id'] == team['id'], f'Identity mismatch: {path}'
    by_key = {}
    for season in data.get('seasons', []):
        key = str(season['key']); assert key not in by_key, f'Duplicate season {path}: {key}'
        assert season.get('coverage') in ('not_loaded', 'partial', 'complete'), f'Invalid coverage: {path}'
        games = season.get('games', []); ids = set()
        for game in games:
            assert game['id'] not in ids, f'Duplicate game: {path}'
            ids.add(game['id'])
            assert game.get('date') and game.get('opponent_name'), f'Incomplete game: {path}'
            assert game.get('sources'), f'Game without provenance: {path}'
            assert game.get('verified') is True, f'Unverified game: {path}'
        if games: assert season.get('sources'), f'Season without provenance: {path}'
        if season['coverage'] == 'not_loaded': assert not games, f'Coverage mismatch: {path}'
        by_key[key] = season
    return by_key

def team_page(team):
    sport = team['sport']; info = SPORTS[sport]; history = load_history(team)
    archive = []
    for key, label in seasons(sport):
        item = {'key': key, 'label': label, 'coverage': 'not_loaded', 'updated_at': None, 'record': None, 'metrics': {}, 'games': [], 'sources': []}
        item.update(history.get(key, {})); item['key'] = key; item['label'] = label; archive.append(item)
    loaded = sum(len(s['games']) for s in archive)
    options = ''.join(f'<option value="{s["key"]}"{" selected" if n == 0 else ""}>{esc(s["label"])} · {"Data pending" if not s["games"] else str(len(s["games"])) + " games"}</option>' for n, s in enumerate(reversed(archive)))
    payload = json.dumps({'team_id': team['id'], 'seasons': archive}, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    affiliation = ' · '.join(v for v in [team['conference'], team['division']] if v)
    features = ''.join(f'<article><h3>{esc(label)}</h3><p>{esc(text)}</p></article>' for label,text in info['features'])
    recent = archive[-1]['label']
    body = f'''<nav class="research-breadcrumbs" aria-label="Breadcrumb"><a href="{BASE}/{sport}/">{info['label']}</a><span aria-hidden="true">/</span><a href="{BASE}/{sport}/teams/">Teams</a><span aria-hidden="true">/</span><span>{esc(team['short_name'])}</span></nav>
<section class="team-research-heading"><img src="{esc(team['logo'])}" alt="{esc(team['name'])} logo" width="94" height="94"><div><p class="research-kicker">{info['label']} · Team research</p><h1>{esc(team['name'])}</h1><p>{esc(affiliation)} · {'2026' if sport == 'mlb' else '2026–27'} membership</p></div></section><nav class="research-tabs" aria-label="Team research sections"><a href="#history">Season history</a><a href="#research">Research coverage</a><a href="{BASE}/{sport}/teams/">All {info['label']} teams</a></nav>
<section class="research-panel" id="history"><div class="history-heading"><div><p class="research-kicker">Season archive · {'2015 onward' if sport == 'mlb' else '2015–16 onward'}</p><h2 id="selected-season-label">{esc(recent)} season</h2></div><div class="season-control"><label for="season-select">Choose a season<select id="season-select">{options}</select></label></div></div><div id="season-content" aria-live="polite"><div class="coverage-message"><span aria-hidden="true">◷</span><div><h3>{'Season archive' if loaded else 'Season data not added yet'}</h3><p>{'Select a season to view collected results.' if loaded else 'Historical results and statistics have not been loaded yet. Choose a season to check coverage.'}</p></div></div></div><noscript><p>Enable JavaScript to switch seasons. Historical coverage is added gradually.</p></noscript></section>
<section class="research-panel" id="research"><h2>What this page will cover</h2><p>As verified data becomes available, this archive will grow into a team research resource. Matchup tools will be built on the same season and game records.</p><div class="research-feature-grid">{features}</div><p class="research-source">Historical conference and division membership will follow each season's source records. Today's affiliation is not applied retroactively.</p></section><p class="research-source">Team identity and logo: <a href="https://www.espn.com/{'mens-college-basketball' if sport == 'cbb' else sport}/team/_/id/{team['espn_id']}">ESPN team directory</a>. Game statistics and betting-line coverage will carry separate sources when added.</p><script type="application/json" id="team-season-data">{payload}</script>'''
    write(f'/{sport}/teams/{team["slug"]}/', f'{team["name"]} History & Season Research', f'{team["name"]} season research archive, with historical data coverage starting in {"2015" if sport == "mlb" else "2015–16"}.', body, indexable=loaded > 0)
    return loaded > 0

def main():
    registry = json.loads((ROOT / 'data/sports/team-registry.json').read_text())
    ids = set(); routes = set(); urls = []
    for team in registry['teams']:
        assert team['id'] not in ids; ids.add(team['id'])
        route = (team['sport'], team['slug']); assert route not in routes; routes.add(route)
        assert re.fullmatch(r'[a-z0-9-]+', team['slug']), team['slug']
        assert team['conference'] and (team['sport'] == 'cbb' or team['division'])
        if team_page(team): urls.append(f'{BASE}/{team["sport"]}/teams/{team["slug"]}/')
    for sport, info in SPORTS.items():
        teams = [t for t in registry['teams'] if t['sport'] == sport]
        directory(sport, teams, registry['membership_checked_at'])
        dashboard_card = f'<article><h3>{info["label"]} Dashboard</h3><p><a href="{BASE}/{sport}/dashboard/">Compare {info["label"]} matchups →</a></p></article>'
        body = f'''<section class="research-intro"><p class="research-kicker">BetWise · {info['label']} research</p><h1>{info['label']} team research.</h1><p>Start with a team. Explore {info['name']} by {'conference' if sport == 'cbb' else 'division'}, then open an individual team's season archive.</p></section><div class="research-feature-grid">{dashboard_card}<article><h3>{len(teams)} team pages</h3><p><a href="{BASE}/{sport}/teams/">Browse all {info['label']} teams →</a></p></article><article><h3>Research guide</h3><p><a href="https://parlaycalculator.bet/resources/{info['guide']}/">Read the {info['label']} betting research guide →</a></p></article><article><h3>Historical research</h3><p>Season archives begin in {'2015' if sport == 'mlb' else '2015–16'}. Results, statistics, and future matchup tools will be added gradually.</p></article></div>'''
        write(f'/{sport}/', f'{info["label"]} Team Research', f'Explore {info["name"]} teams and season research archives with BetWise.', body)
        urls.extend([f'{BASE}/{sport}/', f'{BASE}/{sport}/teams/'])
        urls.append(f'{BASE}/{sport}/dashboard/')
        print(f'{info["label"]}: {len(teams)} team pages')
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + '\n'.join(f'<url><loc>{esc(url)}</loc></url>' for url in urls) + '\n</urlset>\n'
    (ROOT / 'sitemap-sports.xml').write_text(xml)
    print(f'Built {len(ids)} stable team pages, 3 directories and 3 sport hubs. Unpopulated team archives remain noindex until data is added.')

if __name__ == '__main__':
    main()

