#!/usr/bin/env python3
"""Import the user-provided Basketball Reference regular-season team exports.

Usage: python nba/pipeline/import_reference_exports.py --input-dir upload
Input order: seven exports per season, 2015-16 through 2025-26: team per
game, opponent per game, team per 100, opponent per 100, advanced, shooting,
opponent shooting. Original data-stat identifiers and all values are retained.
No games, player stats, betting records or location splits are inferred.
"""
import argparse
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path

TABLES = ['per_game', 'opponent_per_game', 'per_100', 'opponent_per_100',
          'advanced', 'shooting', 'opponent_shooting']

class ExportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None
        self.key = None

    def handle_starttag(self, tag, attrs):
        if tag == 'tr':
            self.row = {}
        if tag in ('th', 'td'):
            self.key = dict(attrs).get('data-stat')
            self.cell = []

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def handle_endtag(self, tag):
        if tag in ('th', 'td') and self.cell is not None:
            if self.key and self.key != 'DUMMY':
                self.row[self.key] = ''.join(self.cell).strip()
            self.cell = None
        if tag == 'tr' and self.row is not None:
            if self.row.get('ranker', '').isdigit():
                self.rows.append(self.row)
            self.row = None

def slug_for(name):
    slug = name.rstrip('*').strip().lower().replace(' ', '-')
    return 'la-clippers' if slug == 'los-angeles-clippers' else slug

def num(row, key, scale=1):
    value = row.get(key)
    if value is None or value == '':
        raise ValueError(f'Missing required field {key} for {row.get("team")}')
    return round(float(value.replace(',', '')) * scale, 3)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'teams' / 'data')
    args = parser.parse_args()
    result = {}
    audit = {'source': 'User-provided Basketball Reference Excel exports',
             'season_type': 'Regular Season', 'seasons': {}}
    expected_teams = None
    for offset, year in enumerate(range(2016, 2027)):
        tables, source_files = {}, []
        for i, table in enumerate(TABLES):
            index = offset * 7 + i
            filename = 'sportsref_download.xls' if index == 0 else f'sportsref_download ({index}).xls'
            path = args.input_dir / filename
            raw = path.read_bytes()
            parsed = ExportParser()
            parsed.feed(raw.decode('utf-8'))
            rows = {slug_for(row['team']): row for row in parsed.rows}
            assert len(parsed.rows) == len(rows) == 30, (year, table, 'team coverage')
            if expected_teams is None:
                expected_teams = set(rows)
            assert set(rows) == expected_teams, (year, table, 'team identities')
            tables[table] = rows
            source_files.append({'table': table, 'filename': filename,
                                 'sha256': hashlib.sha256(raw).hexdigest()})
        total_wins = total_losses = 0
        for slug in sorted(expected_teams):
            t, o, a = (tables[k][slug] for k in ['per_game', 'opponent_per_game', 'advanced'])
            s, os = (tables[k][slug] for k in ['shooting', 'opponent_shooting'])
            games = int(num(t, 'g'))
            wins, losses = int(num(a, 'wins')), int(num(a, 'losses'))
            assert wins + losses == games
            assert all(int(num(tables[k][slug], 'g')) == games for k in TABLES if k != 'advanced')
            assert num(tables['per_100'][slug], 'pts') == num(a, 'off_rtg')
            assert num(tables['opponent_per_100'][slug], 'opp_pts') == num(a, 'def_rtg')
            assert abs(num(a, 'off_rtg') - num(a, 'def_rtg') - num(a, 'net_rtg')) < .11
            for r, prefix in [(t, ''), (o, 'opp_')]:
                for k in ['fg_pct', 'fg3_pct', 'ft_pct']:
                    assert 0 <= num(r, prefix + k) <= 1
            # Distance coverage can omit attempts. Retain source shares without renormalizing.
            assert num(s, 'pct_fga_fg3a') == num(a, 'fg3a_per_fga_pct')
            for k in ['pct_fga_00_03', 'pct_fga_03_10', 'pct_fga_10_16', 'pct_fga_16_xx', 'pct_fga_fg3a']:
                assert 0 <= num(s, k) <= 1
            metrics = {'ppg': num(t, 'pts'), 'points_allowed_per_game': num(o, 'opp_pts'),
                'fg_pct': num(t, 'fg_pct', 100), 'ft_pct': num(t, 'ft_pct', 100),
                'three_pct': num(t, 'fg3_pct', 100), 'opp_fg_pct': num(o, 'opp_fg_pct', 100),
                'opp_three_pct': num(o, 'opp_fg3_pct', 100), 'efg_pct': num(a, 'efg_pct', 100),
                'ortg': num(a, 'off_rtg'), 'drtg': num(a, 'def_rtg'), 'net_rating': num(a, 'net_rtg'),
                'pace': num(a, 'pace'), 'ts_pct': num(a, 'ts_pct', 100),
                'tov_pct': num(a, 'tov_pct'), 'orb_pct': num(a, 'orb_pct'),
                'ft_rate': num(a, 'fta_per_fga_pct', 100),
                'ft_made_rate': num(a, 'ft_rate', 100),
                'opp_efg_pct': num(a, 'opp_efg_pct', 100),
                'opp_tov_pct': num(a, 'opp_tov_pct'), 'drb_pct': num(a, 'drb_pct'),
                'opp_ft_made_rate': num(a, 'opp_ft_rate', 100),
                'three_attempt_rate': num(a, 'fg3a_per_fga_pct', 100),
                'rim_fg_pct': num(s, 'fg_pct_00_03', 100),
                'opp_rim_fg_pct': num(os, 'opp_fg_pct_00_03', 100)}
            row = {'key': str(year), 'label': f'{year-1}–{str(year)[-2:]}',
                   'coverage': 'verified_team_summary', 'season_type': 'Regular Season',
                   'games_played': games, 'record': {'wins': wins, 'losses': losses, 'overall': f'{wins}–{losses}'},
                   'metrics': metrics, 'games': [],
                   'metric_method': 'Basketball Reference season summaries; ratings and pace use Basketball Reference possession estimates.',
                   'sources': [{'name': 'Basketball Reference · regular-season team tables',
                                'url': f'https://www.basketball-reference.com/leagues/NBA_{year}.html'}],
                   'raw_tables': {k: tables[k][slug] for k in TABLES}}
            result.setdefault(slug, {'seasons': []})['seasons'].append(row)
            total_wins += wins
            total_losses += losses
        assert total_wins == total_losses
        assert total_wins == ({2020: 1059, 2021: 1080}.get(year, 1230))
        audit['seasons'][str(year)] = {'teams': 30, 'tables': 7, 'wins': total_wins,
                                     'losses': total_losses, 'source_files': source_files}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for slug, payload in result.items():
        # Preserve independently collected game/player data when reimporting summaries.
        path = args.output_dir / f'{slug}.json'
        prior = json.loads(path.read_text()) if path.exists() else {'seasons': []}
        prior_rows = {str(s['key']): s for s in prior.get('seasons', [])}
        for row in payload['seasons']:
            old = prior_rows.get(row['key'], {})
            prior_rows[row['key']] = {**old, **row, 'games': old.get('games', [])}
        prior['seasons'] = sorted(prior_rows.values(), key=lambda s: s['key'])
        path.write_text(json.dumps(prior, separators=(',', ':'), ensure_ascii=False) + '\n')
    audit['team_seasons'] = 330
    audit['tables'] = 77
    (args.output_dir / 'reference-import-validation.json').write_text(json.dumps(audit, indent=2) + '\n')
    print('Validated 77 tables and 330 team-seasons; preserved all raw table fields.')

if __name__ == '__main__':
    main()
