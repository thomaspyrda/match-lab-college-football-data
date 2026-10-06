#!/usr/bin/env python3
"""Check the published team route graph, season payloads and empty archive policy."""
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
BASE = 'https://matchlab.parlaycalculator.bet'

class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(); self.links = []; self.canonical = None; self.robots = None
        self.seed = ''; self.in_seed = False; self.cards = []; self.options = []
        self.feed(source)
    def handle_starttag(self, tag, attributes):
        a = dict(attributes)
        if tag == 'a' and a.get('href'): self.links.append(a['href'])
        if tag == 'a' and 'data-team-name' in a: self.cards.append(a)
        if tag == 'option' and a.get('value'): self.options.append(a['value'])
        if tag == 'link' and a.get('rel') == 'canonical': self.canonical = a['href']
        if tag == 'meta' and a.get('name') == 'robots': self.robots = a['content']
        if tag == 'script' and a.get('id') == 'team-season-data': self.in_seed = True
    def handle_data(self, text):
        if self.in_seed: self.seed += text
    def handle_endtag(self, tag):
        if tag == 'script': self.in_seed = False

def main():
    registry = json.loads((ROOT/'data/sports/team-registry.json').read_text())
    counts = {'mlb': 30, 'nba': 30, 'cbb': 365}; checked = 0
    for sport, count in counts.items():
        teams = [t for t in registry['teams'] if t['sport'] == sport]
        assert len(teams) == count, (sport, len(teams))
        directory = Page((ROOT/sport/'teams/index.html').read_text())
        assert len(directory.cards) == count
        assert len({c['href'] for c in directory.cards}) == count
        assert directory.canonical == f'{BASE}/{sport}/teams/'
        assert len({c['data-group'] for c in directory.cards}) == (32 if sport == 'cbb' else 6)
        for team in teams:
            path = f'/{sport}/teams/{team["slug"]}/'
            page = Page((ROOT/path.lstrip('/')/'index.html').read_text())
            assert page.canonical == BASE + path
            payload = json.loads(page.seed)
            assert payload['team_id'] == team['id']
            seasons = payload['seasons']; expected_first = '2015' if sport == 'mlb' else '2016'
            assert seasons[0]['key'] == expected_first
            assert len(set(s['key'] for s in seasons)) == len(seasons)
            assert set(page.options) == {s['key'] for s in seasons}
            games = sum(len(s['games']) for s in seasons)
            assert ('noindex' in page.robots) == (games == 0)
            for link in page.links:
                url = urlparse(link)
                if url.netloc == urlparse(BASE).netloc and url.path.startswith(('/mlb/', '/nba/', '/cbb/')):
                    assert (ROOT/url.path.lstrip('/')/'index.html').exists(), link
            checked += 1
    # Exercise future ingestion guardrails with a small isolated source fixture.
    import tempfile
    from unittest.mock import patch
    spec = importlib.util.spec_from_file_location('sport_builder', ROOT/'build_sport_team_pages.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    team = registry['teams'][0]
    with tempfile.TemporaryDirectory() as folder, patch.object(module, 'ROOT', Path(folder)):
        path = Path(folder)/'data/sports'/team['sport']/'teams'/f'{team["espn_id"]}.json'
        path.parent.mkdir(parents=True)
        assert module.load_history(team) == {}
        data = {'schema_version':1,'team_id':team['id'],'seasons':[{'key':'2015','coverage':'partial','sources':[{'name':'Fixture','url':'https://example.com'}],'games':[{'id':'fixture:1','date':'2015-04-01','opponent_name':'Fixture opponent','verified':True,'sources':[{'name':'Fixture','url':'https://example.com/game'}]}]}]}
        path.write_text(json.dumps(data)); assert len(module.load_history(team)['2015']['games']) == 1
        data['seasons'][0]['games'][0]['verified'] = False; path.write_text(json.dumps(data))
        try: module.load_history(team)
        except AssertionError: pass
        else: raise AssertionError('Unverified game accepted')
        data['team_id'] = 'wrong:sport:team'; path.write_text(json.dumps(data))
        try: module.load_history(team)
        except AssertionError: pass
        else: raise AssertionError('Mismatched team identity accepted')
    print(f'Verified {checked} team routes, directory grouping, season selectors, canonicals, coverage and ingestion guardrails.')

if __name__ == '__main__': main()
