#!/usr/bin/env python3
"""Build regular-season schedules and team-specific player totals.

Usage: python nba/pipeline/import_season_details.py --source-dir /path/to/sources
Sources: gamelog_YEAR.parquet (llimllib/nba_data NBA TeamGameLogs),
sdv-team-YEAR.csv (SportsDataverse NBA BoxScoreTraditionalV3), and
player-totals.csv (sumitrodatta/nba-alt-awards Basketball Reference export).
Only NBA regular-season games and individual team stints are imported.
Requires pandas and pyarrow. No betting lines are inferred.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'teams' / 'data'
BREF_CODES = {'BKN': 'BRK', 'CHA': 'CHO', 'PHX': 'PHO'}
CATEGORIES = {'points': 'pts', 'rebounds': 'trb', 'assists': 'ast',
              'steals': 'stl', 'blocks': 'blk', 'threes': 'x3p'}
TOTALS = {'minutes': 'mp', 'points': 'pts', 'rebounds': 'trb', 'assists': 'ast',
          'steals': 'stl', 'blocks': 'blk', 'turnovers': 'tov', 'fg_made': 'fg',
          'fg_attempts': 'fga', 'three_made': 'x3p', 'three_attempts': 'x3pa',
          'ft_made': 'ft', 'ft_attempts': 'fta',
          'offensive_rebounds': 'orb', 'defensive_rebounds': 'drb'}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':'),
                               allow_nan=False) + '\n')


def ratio(made, attempted):
    return made / attempted if attempted else None


def build(source):
    players_path = source / 'player-totals.csv'
    raw = pd.read_csv(players_path)
    players = raw[(raw.lg == 'NBA') & raw.season.between(2016, 2026)
                  & ~raw.team.str.contains(r'TM|TOT')].copy()
    assert not players.duplicated(['season', 'player_id', 'team']).any()
    assert players.g.gt(0).all()
    outputs, checks, corrections, source_files = {}, [], [], []
    source_files.append(players_path)
    for year in range(2016, 2027):
        log_path = source / f'gamelog_{year}.parquet'
        box_path = source / f'sdv-team-{year}.csv'
        source_files.extend([log_path, box_path])
        logs = pd.read_parquet(log_path)
        logs = logs[logs.game_id.str.startswith('002')].copy()
        boxes = pd.read_csv(box_path, dtype={'game_id': str})
        boxes.game_id = boxes.game_id.str.zfill(10)
        boxes = boxes[(boxes.season_type_id == 2)
                      & boxes.game_id.str.startswith('002')].copy()
        assert not logs.duplicated(['game_id', 'team_id']).any()
        assert not boxes.duplicated(['game_id', 'team_id']).any()
        games = logs.merge(boxes, on=['game_id', 'team_id'], validate='one_to_one',
                           suffixes=('', '_box'))
        assert len(games) == len(logs) == len(boxes), f'{year}: incomplete coverage'
        assert games.team_id.nunique() == 30
        pairs = {}
        for game_id, pair in games.groupby('game_id'):
            assert len(pair) == 2 and set(pair.side) == {'home', 'away'}
            a, b = pair.to_dict('records')
            assert a['points'] != b['points']
            for team, opponent in [(a, b), (b, a)]:
                assert team['wl'] == ('W' if team['points'] > opponent['points'] else 'L')
                assert team['points'] == (2 * team['field_goals_made']
                                          + team['three_pointers_made']
                                          + team['free_throws_made'])
                pairs[(game_id, team['team_id'])] = opponent
                if team['pts'] != team['points']:
                    corrections.append({'season': year, 'game_id': game_id,
                                        'team': team['team_abbreviation'],
                                        'archived_score': int(team['pts']),
                                        'verified_score': int(team['points']),
                                        'source': f'https://www.nba.com/game/{game_id}/box-score'})
        season_players = players[players.season == year]
        combined = season_players.groupby('player_id')[list(CATEGORIES.values())].sum()
        ranks = {category: combined[column].rank(method='min', ascending=False).astype(int).to_dict()
                 for category, column in CATEGORIES.items()}
        for name, team_games in games.groupby('team_name'):
            slug = name.lower().replace(' ', '-')
            team_games = team_games.sort_values(['game_date', 'game_id'])
            archive = json.loads((DATA / f'{slug}.json').read_text())
            summary = next(s for s in archive['seasons'] if s['key'] == str(year))
            wins = int((team_games.wl == 'W').sum())
            losses = int((team_games.wl == 'L').sum())
            assert len(team_games) == summary['games_played']
            assert wins == summary['record']['wins'] and losses == summary['record']['losses']
            assert abs(team_games.points.mean() - summary['metrics']['ppg']) <= .051
            abbreviation = team_games.team_abbreviation.iloc[0]
            code = BREF_CODES.get(abbreviation, abbreviation)
            roster = season_players[season_players.team == code]
            assert len(roster) >= 10
            assert roster.g.max() <= len(team_games)
            assert int(roster.pts.sum()) == int(team_games.points.sum()), f'{year} {code}: player point totals'
            player_rows = []
            for row in roster.to_dict('records'):
                total = {key: int(row[col]) for key, col in TOTALS.items()}
                assert total['points'] == (2 * total['fg_made'] + total['three_made'] + total['ft_made'])
                per_game = {key: total[key] / int(row['g']) for key in
                            ['minutes', 'points', 'rebounds', 'assists', 'steals', 'blocks', 'turnovers']}
                per_game.update({
                    'fg_pct': ratio(total['fg_made'], total['fg_attempts']),
                    'three_pct': ratio(total['three_made'], total['three_attempts']),
                    'ft_pct': ratio(total['ft_made'], total['ft_attempts']),
                    'efg_pct': ratio(total['fg_made'] + .5 * total['three_made'], total['fg_attempts']),
                    'threes': total['three_made'] / int(row['g']),
                })
                player_rows.append({'id': row['player_id'], 'name': row['player'],
                                    'position': row['pos'] if pd.notna(row['pos']) else None, 'games': int(row['g']),
                                    'starts': int(row['gs']), 'totals': total,
                                    'per_game': per_game,
                                    'league_ranks': {category: ranks[category][row['player_id']]
                                                     for category in CATEGORIES},
                                    'league_totals': {category: int(combined.loc[row['player_id'], col])
                                                      for category, col in CATEGORIES.items()}})
            player_rows.sort(key=lambda p: (-p['totals']['points'], -p['games'], p['name']))
            leaders = {}
            for category in CATEGORIES:
                total_key = 'three_made' if category == 'threes' else category
                largest = max(p['totals'][total_key] for p in player_rows)
                leaders[category] = [p['id'] for p in player_rows if largest > 0 and p['totals'][total_key] == largest]
            schedule, cumulative_w, cumulative_l = [], 0, 0
            for number, g in enumerate(team_games.to_dict('records'), 1):
                opponent = pairs[(g['game_id'], g['team_id'])]
                cumulative_w += g['wl'] == 'W'
                cumulative_l += g['wl'] == 'L'
                minutes = int(str(g['minutes']).split(':')[0])
                overtime = max(0, round((minutes / 5 - 48) / 5))
                schedule.append({'game_id': g['game_id'], 'game_number': number,
                                 'date': str(g['game_date'])[:10],
                                 'location': 'Home' if g['side'] == 'home' else 'Away',
                                 'neutral': year == 2020 and str(g['game_date'])[:10] >= '2020-07-30',
                                 'opponent_name': opponent['team_name'],
                                 'opponent_slug': opponent['team_name'].lower().replace(' ', '-'),
                                 'opponent_abbreviation': opponent['team_abbreviation'],
                                 'result': g['wl'], 'score_for': int(g['points']),
                                 'score_against': int(opponent['points']),
                                 'overtime': overtime,
                                 'record_after': f'{cumulative_w}–{cumulative_l}'})
            payload = {'season_type': 'Regular Season', 'games_played': len(schedule),
                       'record': f'{wins}–{losses}', 'games': schedule,
                       'players': player_rows, 'leaders': leaders,
                       'sources': {'schedule': 'https://www.nba.com/stats/teams/boxscores-traditional',
                                   'players': f'https://www.basketball-reference.com/leagues/NBA_{year}_totals.html'}}
            outputs.setdefault(slug, {'seasons': {}})['seasons'][str(year)] = payload
            checks.append({'team': slug, 'season': year, 'games': len(schedule),
                           'players': len(player_rows), 'record': payload['record'],
                           'points': int(team_games.points.sum()), 'player_points_match': True})
    assert len(outputs) == 30 and len(checks) == 330
    assert sum(len(v['players']) for t in outputs.values() for v in t['seasons'].values()) == len(players)
    for slug, payload in outputs.items():
        payload['method'] = ('NBA regular-season game logs joined to final NBA traditional box scores. '
                             'Basketball Reference player totals for each team stint; combined multi-team rows excluded. '
                             'Leader selection uses team season totals; NBA ranks use combined season totals across all teams, with ties sharing ranks.')
        save(DATA / f'{slug}-season-details.json', payload)
    audit = {'status': 'passed', 'team_seasons': len(checks),
             'unique_games': sum(c['games'] for c in checks) // 2,
             'player_team_seasons': len(players), 'checks': checks,
             'score_corrections': corrections,
             'sources': {'nba_game_logs_mirror': 'https://github.com/llimllib/nba_data',
                         'nba_box_scores_mirror': 'https://github.com/sportsdataverse/sportsdataverse-data/releases/tag/nba_stats_team_boxscores',
                         'basketball_reference_mirror': 'https://github.com/sumitrodatta/nba-alt-awards/blob/main/2026/Data/Player%20Totals.csv'},
             'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}}
    save(DATA / 'season-details-validation.json', audit)
    print(json.dumps({k: audit[k] for k in ['status', 'team_seasons', 'unique_games', 'player_team_seasons']}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-dir', required=True, type=Path)
    build(parser.parse_args().source_dir)
