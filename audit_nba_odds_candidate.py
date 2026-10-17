#!/usr/bin/env python3
"""Audit candidate NBA odds CSV against existing 2015-16 team games and Covers.

The candidate's Spread column is an unsigned magnitude; infer favorite from
moneylines where unambiguous. Never publish lines merely because scores match.
Usage: python audit_nba_odds_candidate.py /path/to/nba_odds_clean.csv
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXPECTED_ATS=(42,39,1)  # Covers 2015-16 Atlanta regular season
EXPECTED_OU=(38,44,0)

def audit(path):
    rows=list(csv.DictReader(Path(path).open(newline='')))
    games=json.loads((ROOT/'nba/teams/data/atlanta-hawks-season-details.json').read_text())['seasons']['2016']['games']
    result={'matched':0,'score_mismatches':[],'ambiguous_moneylines':[],'ats':Counter(),'ou':Counter()}
    for game in games:
        candidates=[r for r in rows if r['Date']==game['date'] and 'Atlanta Hawks' in (r['Home'],r['Away'])]
        if len(candidates)!=1:raise ValueError(f"{game['game_id']}: expected one date/team match, got {len(candidates)}")
        row=candidates[0];is_home=row['Home']=='Atlanta Hawks'
        own=game['score_for'];opp=game['score_against']
        if own+opp!=float(row['Points']) or (own-opp if is_home else opp-own)!=float(row['Win_Margin']):
            result['score_mismatches'].append(game['game_id']);continue
        result['matched']+=1
        total_margin=own+opp-float(row['OU'])
        result['ou']['Over' if total_margin>0 else 'Under' if total_margin<0 else 'Push']+=1
        try:
            home_ml=float(row['ML_Home']);away_ml=float(row['ML_Away'])
            if home_ml==away_ml:raise ValueError('equal prices')
            home_spread=-abs(float(row['Spread'])) if home_ml<away_ml else abs(float(row['Spread']))
            ats_margin=own-opp+(home_spread if is_home else -home_spread)
            result['ats']['W' if ats_margin>0 else 'L' if ats_margin<0 else 'P']+=1
        except (TypeError,ValueError):
            result['ambiguous_moneylines'].append(game['game_id'])
    ats=tuple(result['ats'][x] for x in ('W','L','P'))
    ou=tuple(result['ou'][x] for x in ('Over','Under','Push'))
    return {'matched':result['matched'],'score_mismatches':result['score_mismatches'],
            'ambiguous_moneylines':result['ambiguous_moneylines'],'ats':ats,'ou':ou,
            'covers_ats':EXPECTED_ATS,'covers_ou':EXPECTED_OU,
            'publish_approved':result['matched']==82 and not result['score_mismatches'] and not result['ambiguous_moneylines'] and ats==EXPECTED_ATS and ou==EXPECTED_OU}

if __name__=='__main__':
    print(json.dumps(audit(sys.argv[1]),indent=2))
