#!/usr/bin/env python3
"""Publish one shared sport menu on current and archived pages.
Only navigation markup and its asset references are changed; season data is untouched.
"""
import argparse
import json
import re
from pathlib import Path

NAV_URL = "https://matchlab.parlaycalculator.bet/site-navigation-v10.js?v=20261022-mlb-rankings"
CSS_URL = "https://matchlab.parlaycalculator.bet/site-navigation.css?v=20261021-1"
SPORTS = json.loads(r'''{"NFL":[["NFL Dashboard","https://nfl.parlaycalculator.bet/"],["NFL Teams","https://nfl.parlaycalculator.bet/teams.html"],["Rankings","https://nfl.parlaycalculator.bet/nfl-team-strength-rankings/"]],"CFB":[["CFB Dashboard","https://matchlab.parlaycalculator.bet/cfb-dashboard-preview/"],["CFB Teams","https://matchlab.parlaycalculator.bet/teams.html"],["CFB Match Lab","https://matchlab.parlaycalculator.bet/"],["Rankings","https://matchlab.parlaycalculator.bet/college-football-team-strength-rankings/"]],"MLB":[["MLB Dashboard","https://matchlab.parlaycalculator.bet/mlb/dashboard/"],["MLB Teams","https://matchlab.parlaycalculator.bet/mlb/teams/"],["Rankings","https://matchlab.parlaycalculator.bet/mlb/rankings/"]],"NBA":[["NBA Dashboard","https://matchlab.parlaycalculator.bet/nba/dashboard/"],["NBA Teams","https://matchlab.parlaycalculator.bet/nba/teams/"],["Rankings","https://matchlab.parlaycalculator.bet/nba/rankings/"]],"CBB":[["CBB Dashboard","https://matchlab.parlaycalculator.bet/cbb/dashboard/"],["CBB Teams","https://matchlab.parlaycalculator.bet/cbb/teams/"]]}''')
NBA_RANKINGS = "https://matchlab.parlaycalculator.bet/nba/rankings/"
NAV_TAG = re.compile(r'(<nav\b[^>]*>)(.*?)(</nav>)', re.I | re.S)
JS_REF = re.compile(r"""(src\s*=\s*)(["'])(?:https?://[^"'<>\s]+)?/?site-navigation(?:-v\d+)?\.js(?:\?[^"'<>]*)?\2""", re.I)
CSS_REF = re.compile(r"""(href\s*=\s*)(["'])(?:https?://[^"'<>\s]+)?/?site-navigation\.css(?:\?[^"'<>]*)?\2""", re.I)

def menu_html(sport):
    links = ['<a href="https://parlaycalculator.bet/betwise/">Why BetWise?</a>']
    for label, entries in SPORTS.items():
        active = ' active-sport' if sport == label else ''
        anchors = ''.join(f'<a href="{url}">{text}</a>' for text, url in entries)
        links.append(f'<details class="sport-menu{active}"><summary>{label}<span aria-hidden="true">⌄</span></summary><div class="sport-dropdown">{anchors}</div></details>')
    links.extend(['<a href="https://parlaycalculator.bet/#calculator">Parlay Calculator</a>', '<a href="https://parlaycalculator.bet/resources/">All Resources</a>'])
    return ''.join(links)

def is_shared_nav(tag):
    return bool(re.search(r"""class\s*=\s*["'][^"']*\bsite-nav\b|aria-label\s*=\s*["'](?:Primary|Mobile) navigation["']""", tag, re.I))

def normalize(source, sport):
    menu = menu_html(sport)
    nav_count = 0
    def replace_nav(match):
        nonlocal nav_count
        if not is_shared_nav(match[1]):
            return match[0]
        nav_count += 1
        return match[1] + menu + match[3]
    updated = NAV_TAG.sub(replace_nav, source)
    updated, script_count = JS_REF.subn(lambda m: m[1] + m[2] + NAV_URL + m[2], updated)
    updated, style_count = CSS_REF.subn(lambda m: m[1] + m[2] + CSS_URL + m[2], updated)
    if nav_count:
        assets = ''
        if not script_count:
            assets += f'<script defer src="{NAV_URL}"></script>'
        if not style_count:
            assets += f'<link rel="stylesheet" href="{CSS_URL}">'
        if assets:
            updated = re.sub(r'</head>', lambda m: assets + m[0], updated, count=1, flags=re.I)
        assert NAV_URL in updated, "Shared navigation must load the canonical script"
        for tag in NAV_TAG.finditer(updated):
            if is_shared_nav(tag[1]):
                assert NBA_RANKINGS in tag[2], "NBA Rankings must exist in every shared menu"
    return updated, nav_count, script_count

def self_test():
    sample = """<html><head><script defer src="/site-navigation-v10.js?v=20261022-tophero"></script></head><body><nav class="site-nav">old</nav><details class="mobile-menu"><nav aria-label="Mobile navigation">old</nav></details><main><table><tr><td>Archived stats 112.5</td></tr></table></main></body></html>"""
    result, menus, _ = normalize(sample, 'NFL')
    assert menus == 2 and result.count(NBA_RANKINGS) == 2
    assert '<main><table><tr><td>Archived stats 112.5</td></tr></table></main>' in result
    assert normalize(result, 'NFL')[0] == result
    assert normalize('<html><meta http-equiv="refresh" content="0;url=/teams.html"></html>', 'NFL')[0].startswith('<html><meta')
    print("Shared navigation checks passed")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--sport', default=None)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    self_test()
    changed = menus = wired = pages = 0
    failures = []
    for path in args.root.rglob('*.html'):
        if any(part in {'.git', 'node_modules'} for part in path.relative_to(args.root).parts):
            continue
        pages += 1
        first = path.relative_to(args.root).parts[0].upper()
        sport = args.sport or (first if first in {'NBA', 'MLB', 'CBB'} else 'CFB')
        original = path.read_text(encoding='utf-8')
        updated, count, refs = normalize(original, sport)
        menus += count
        wired += bool(count or refs)
        if updated != original:
            changed += 1
            if args.check:
                failures.append(str(path))
            else:
                path.write_text(updated, encoding='utf-8')
    print(f"Audited {pages} HTML pages; {wired} shared-navigation pages, {menus} menus, {changed} changed")
    if failures:
        raise SystemExit("Navigation normalization required: " + ', '.join(failures[:10]))

if __name__ == '__main__':
    main()

