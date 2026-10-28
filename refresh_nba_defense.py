"""Collect publicly displayed, season-specific scoring allowed by position.

Position labels follow Hashtag Basketball's classification, not guessed G/F
splits from ESPN. Reject incomplete tables and exclude badge/rank numbers.
"""
import argparse
import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
SOURCE = 'https://hashtagbasketball.com/nba-defense-vs-position'
POSITIONS = ('PG', 'SG', 'SF', 'PF', 'C')


def clean(value):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>', ' ', value)).split())


def parse(source, registry, year):
    selected = re.search(r'<option\s+selected="selected"\s+value="1">Show data from the entire (\d{4})-(\d{2}) NBA Season', source)
    if not selected or int(selected[1]) + 1 != year:
        raise ValueError('Defense-vs-position page is not showing the requested season')
    updated = re.search(r'Updated:</strong>\s*(\d{1,2} \w+ \d{4})', source)
    if not updated:
        raise ValueError('Missing defense-vs-position source date')
    date = datetime.strptime(updated[1], '%d %B %Y').date().isoformat()
    if date > datetime.now(timezone.utc).date().isoformat():
        raise ValueError('Defense source date is in the future')
    lookup = {t['abbreviation']: t['slug'] for t in registry['teams'] if t['sport'] == 'nba'}
    for alias, official in {'GS':'GSW', 'NO':'NOP', 'NY':'NYK', 'PHO':'PHX', 'SA':'SAS', 'WAS':'WSH', 'UTA':'UTAH'}.items():
        lookup[alias] = lookup.get(official) or lookup.get(alias)
        if not lookup[alias]:raise ValueError('Unknown NBA abbreviation '+alias)
    table = re.search(r'<table\b[^>]*\bid="ContentPlaceHolder1_GridView1"[^>]*>(.*?)</table>', source, re.S)
    if not table or 'PTS' not in clean(table[1]):
        raise ValueError('Missing full defense-vs-position points table')
    teams = {}
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>', table[1], re.S):
        cells = re.findall(r'<td\b[^>]*>(.*?)</td>', row, re.S)
        if not cells:
            continue
        if len(cells) != 11:
            raise ValueError('Changed defense table columns')
        position, abbreviation = clean(cells[0]), clean(cells[1]).split()[0]
        # The first span is the value; the later badge is the provider's rank.
        score = re.search(r'<span\b[^>]*\bid="[^"]*Label2_[^"]*"[^>]*>([^<]+)</span>', cells[2])
        if position not in POSITIONS or abbreviation not in lookup or not score:
            raise ValueError('Unknown defense-vs-position row')
        points = float(score[1])
        if not 0 <= points <= 100:
            raise ValueError('Invalid scoring allowed by position')
        target = teams.setdefault(lookup[abbreviation], {})
        if position in target:
            raise ValueError('Duplicate defense-vs-position row')
        target[position] = points
    if len(teams) != 30 or any(set(row) != set(POSITIONS) for row in teams.values()):
        raise ValueError('Expected all 150 team/position observations')
    return {'season': year, 'as_of': date, 'source': SOURCE,
            'methodology': 'Opponent points per game by the provider-listed position; not individual on-court defensive matchup assignments.',
            'teams': teams}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-html', type=Path)
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    year = now.year + (now.month >= 7)
    if args.source_html:
        body = args.source_html.read_text()
    else:
        req = Request(SOURCE, headers={'User-Agent':'Mozilla/5.0 BetWiseResearch/1.0'})
        with urlopen(req, timeout=30) as response:
            body = response.read().decode('utf-8')
    registry = json.loads((ROOT/'data/sports/team-registry.json').read_text())
    output = parse(body, registry, year)
    output['fetched_at'] = now.isoformat()
    path = ROOT/'nba/rankings/data/defense-by-position.json'
    path.write_text(json.dumps(output, ensure_ascii=False, separators=(',',':'))+'\n')
    print('Updated all 150 scoring-allowed observations; source date:', output['as_of'])


if __name__ == '__main__':
    main()
