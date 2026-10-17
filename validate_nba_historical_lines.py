#!/usr/bin/env python3
"""Validate sourced historical NBA lines against existing season-detail game records.

Input JSON rows must contain game_id, source, source_url, team_spread,
closing_total, and (optionally) line_type. Missing quotes remain missing.
Does not modify team pages. Never identify an unverified quote as closing.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def grade(game, quote):
    assert str(game['game_id']) == str(quote['game_id']), 'NBA game ID mismatch'
    if not quote.get('source') or not quote.get('source_url'):
        raise ValueError('Source and URL required')
    if quote.get('line_type') not in ('opening', 'closing_verified', 'published_unspecified'):
        raise ValueError('Line type must be explicit')
    spread=quote.get('team_spread')
    total=quote.get('total')
    if spread is None or total is None:
        raise ValueError('Both spread and total required for this validation test')
    spread=float(spread)
    total=float(total)
    point_diff=game['score_for']-game['score_against']
    ats_margin=point_diff+spread
    ou_margin=game['score_for']+game['score_against']-total
    return {'game_id':str(game['game_id']),'spread':spread,'ats':'W' if ats_margin>0 else 'L' if ats_margin<0 else 'P',
            'total':total,'ou':'Over' if ou_margin>0 else 'Under' if ou_margin<0 else 'Push',
            'line_type':quote['line_type'],'source':quote['source'],'source_url':quote['source_url']}

def find_game(team_slug, season, game_id):
    path=ROOT/'nba/teams/data'/f'{team_slug}-season-details.json'
    seasons=json.loads(path.read_text())['seasons']
    return next(g for g in seasons[str(season)]['games'] if str(g['game_id'])==str(game_id))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('team_slug')
    p.add_argument('season',type=int)
    p.add_argument('quotes_json',type=Path)
    p.add_argument('--expected-ats', help='Covers ATS wins-losses-pushes, e.g. 42-39-1')
    p.add_argument('--expected-ou', help='Covers O/U overs-unders-pushes, e.g. 38-44-0')
    args=p.parse_args()
    input_rows=json.loads(args.quotes_json.read_text())
    ids=[str(x['game_id']) for x in input_rows]
    if len(ids)!=len(set(ids)):
        raise SystemExit('Duplicate game IDs in imported quotes')
    results=[]
    for quote in input_rows:
        game=find_game(args.team_slug,args.season,quote['game_id'])
        results.append(grade(game,quote))
    ats=[sum(x['ats']==v for x in results) for v in ('W','L','P')]
    ou=[sum(x['ou']==v for x in results) for v in ('Over','Under','Push')]
    expected_ats=list(map(int,args.expected_ats.split('-'))) if args.expected_ats else None
    expected_ou=list(map(int,args.expected_ou.split('-'))) if args.expected_ou else None
    checks={'ats': expected_ats is not None and ats==expected_ats,
            'ou': expected_ou is not None and ou==expected_ou}
    report={'matched':len(results),'ats':ats,'ou':ou,'expected_ats':expected_ats,
            'expected_ou':expected_ou,'checks':checks,'ready_to_publish':all(checks.values()),'results':results}
    print(json.dumps(report,indent=2))
    if not report['ready_to_publish']:
        raise SystemExit('Backfill is incomplete or fails Covers season totals; do not publish')
