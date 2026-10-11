#!/usr/bin/env python3
"""Game-level audit for 10% market MOV test, no production changes."""
import json, os, pathlib, urllib.request, urllib.parse
from collections import defaultdict
R=pathlib.Path(__file__).resolve().parent
existing=json.loads((R/'data/experiments/closing_mov_10pct_pregame_comparison_2026.json').read_text())
games=[g for g in json.loads((R/'data/historical/2026.json').read_text())['games'] if g.get('result') and 0<int(g.get('week') or 0)<7]
key=os.environ['CFBD_API_KEY']
url='https://api.collegefootballdata.com/lines?'+urllib.parse.urlencode({'year':2026,'seasonType':'regular'})
req=urllib.request.Request(url,headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
with urllib.request.urlopen(req,timeout=120) as f:lines=json.load(f)
by_id={str(r['id']):r for r in lines}
teams=['New Mexico','SMU','Oklahoma']
result={}
for team in teams:
    rows=[]
    for g in sorted(games,key=lambda g:(g.get('week',0),g.get('start_date',''))):
        home=g.get('home');away=g.get('away')
        if team not in (home,away):continue
        is_home=team==home;opp=away if is_home else home
        hp=float(g['result']['home_points']);ap=float(g['result']['away_points'])
        margin=(hp-ap)*(1 if is_home else -1)
        line=by_id.get(str(g['game_id']))
        providers=sorted((p for p in ((line or {}).get('lines') or []) if p.get('spread') is not None),key=lambda p:(0 if 'consensus' in str(p.get('provider','')).lower() else 1,0 if 'draftkings' in str(p.get('provider','')).lower() else 1,str(p.get('provider',''))))
        spread=None;adjusted=None;provider=None
        if providers:
            p=providers[0];provider=p.get('provider');spread=float(p['spread'])*(1 if is_home else -1)
            adjusted=max(-35,min(35,margin+spread))
        rows.append({'week':g['week'],'opponent':opp,'home':is_home,'points_for':hp if is_home else ap,
             'points_against':ap if is_home else hp,'actual_margin':margin,
             'team_spread':spread,'mov_residual':adjusted,'provider':provider,'game_id':str(g['game_id'])})
    covered=[r['mov_residual'] for r in rows if r['mov_residual'] is not None]
    source=next(x for x in existing['rankings'] if x['team']==team)
    result[team]={'games':rows,'covered_games':len(covered),'total_games':len(rows),
       'sum_residual':round(sum(covered),2),'mean_residual':round(sum(covered)/len(covered),3) if covered else None,
       'shrunken_mean_residual':round(sum(covered)/(len(covered)+4),3) if covered else None,
       'mov_standardized_sd':source['mov_sd'],'baseline_rank':source['baseline_rank'],
       'adjusted_rank':source['mov_rank'],'adjusted_score':source['combined_score']}
assert all(result[t]['covered_games']==next(x for x in existing['rankings'] if x['team']==t)['games_with_lines'] for t in teams)
out={'season':2026,'through_week':6,'method':'Same provider sorting, per-game caps and sample as 10% MOV experiment. Team spread uses home-team negative favorite convention.','teams':result,
'warning':'CFBD market line records are not guaranteed timestamp-certified kickoff closing odds; game-by-game data are market estimates, not verified closing lines.'}
path=R/'data/experiments/closing_mov_three_team_game_audit_2026.json'
path.write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(result,indent=2))
