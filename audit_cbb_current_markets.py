#!/usr/bin/env python3
"""Audit verified current-season CBB market coverage without inventing lines."""
import json
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
YEAR=2027

def audit():
    registry=json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams']
    slugs={str(t['espn_id']):t['slug'] for t in registry if t['sport']=='cbb'}
    games={}
    for tid,slug in slugs.items():
        path=ROOT/'data/cbb/teams'/f'{slug}.json'
        if not path.exists():continue
        data=json.loads(path.read_text()).get('seasons',{}).get(str(YEAR),{})
        market=ROOT/'data/cbb/markets'/f'{slug}.json'
        markets=json.loads(market.read_text()).get('games',{}).get(str(YEAR),{}) if market.exists() else {}
        for phase in data.get('phases',{}).values():
            for game in phase.get('games',[]):
                if game.get('status')!='final':continue
                gid=str(game['id'])
                entry=games.setdefault(gid,{'id':gid,'date':game['date'],'teams':[],'spread_verified':False,'total_verified':False})
                if tid not in entry['teams']:entry['teams'].append(tid)
                odds=markets.get(gid,{})
                if odds.get('ats') in ('W','L','P'):entry['spread_verified']=True
                if odds.get('ou') in ('O','U','P'):entry['total_verified']=True
    missing=[g for g in games.values() if not(g['spread_verified'] and g['total_verified'])]
    report={'season':YEAR,'generated_at':datetime.now(timezone.utc).isoformat(),
            'completed_games':len(games),'spread_verified':sum(g['spread_verified'] for g in games.values()),
            'total_verified':sum(g['total_verified'] for g in games.values()),
            'fully_verified':len(games)-len(missing),'unverified_games':missing}
    output=ROOT/'data/cbb/market-coverage-2027.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('Market coverage',json.dumps({k:v for k,v in report.items() if k!='unverified_games'}))
    if missing:print('First missing games',json.dumps(missing[:10]))
    return report
if __name__=='__main__':audit()
