#!/usr/bin/env python3
"""BetWise CBB v1: frozen preseason order, chronological opponent adjustment.
No odds, polls, paint totals, recruiting or player-availability guesses are inputs.
"""
from __future__ import annotations
import argparse,json,math,statistics
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
FORM_WEIGHTS=(1.60,1.50,1.40,1.30,1.20,1.10,1.05) # newest first
BASELINE=105.0
HOME_NET_ADVANTAGE=4.0 # points per 100 possessions; neutral games get zero

def anchor_weight(games): return max(0.0,1-games/12)
def weighted_mean(values):
    if not values:return None
    weights=[FORM_WEIGHTS[i] if i<len(FORM_WEIGHTS) else 1.0 for i in range(len(values))]
    return sum(v*w for v,w in zip(reversed(values),weights))/sum(weights)
def non_d1_penalty(margin):
    if margin>=15:return 0.0
    if margin>=11:return 0.5
    if margin>=6:return 1.0
    if margin>=1:return 2.0
    return 3.0+min(3.0,abs(margin)*0.10)
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
def finite(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def possessions(boxes):
    required=('points','fgm','fga','tpm','ftm','fta','oreb','tov')
    for b in boxes:
        if not all(finite(b.get(k)) and b[k]>=0 for k in required):raise ValueError('Incomplete possession box')
        if b['fgm']>b['fga'] or b['tpm']>b['fgm'] or b['ftm']>b['fta']:raise ValueError('Invalid shooting box')
        if abs(2*b['fgm']+b['tpm']+b['ftm']-b['points'])>.01:raise ValueError('Shooting does not reconcile to final score')
    p=sum(b['fga']-b['oreb']+b['tov']+.475*b['fta'] for b in boxes)/2
    if not 35<=p<=160:raise ValueError('Implausible possessions')
    return p

def calculate(seed,ledger,registry,now=None,previous=None):
    now=now or datetime.now(timezone.utc)
    known={str(t['team_id']):t for t in seed['teams']}
    if len(known)<350 or len(known)!=len(seed['teams']):raise ValueError('Incomplete or duplicate preseason seed')
    reg={str(t['espn_id']):t for t in registry if t['sport']=='cbb'}
    if set(known)!=set(reg):raise ValueError('Preseason and D1 membership mismatch')
    if ledger['season']!=seed['season']:raise ValueError('Season mismatch')
    observations=defaultdict(list); penalties=defaultdict(float);records=defaultdict(lambda:[0,0]);non_d1=defaultdict(int)
    initial={i:(BASELINE+t['initial_net_rating']/2,BASELINE-t['initial_net_rating']/2) for i,t in known.items()}
    current=dict(initial);schedules=defaultdict(list);audit=[]
    def ratings(i):
        obs=observations[i];w=anchor_weight(len(obs))
        if not obs:return initial[i]
        return tuple(w*initial[i][j]+(1-w)*weighted_mean([o[j] for o in obs]) for j in (0,1))
    games=sorted(ledger.get('games',[]),key=lambda g:(g['date'],str(g['id'])))
    seen=set();byday=defaultdict(list)
    for g in games:
        if g.get('season')!=seed['season'] or g.get('phase') not in (2,3):raise ValueError('Wrong season or exhibition in ledger')
        if str(g['id']) in seen:raise ValueError('Duplicate game')
        seen.add(str(g['id']))
        dt=datetime.fromisoformat(g['date'].replace('Z','+00:00'))
        if dt>=now:raise ValueError('Future game')
        day=dt.astimezone(ZoneInfo('America/New_York')).date().isoformat();byday[day].append(g)
    for day,daygames in sorted(byday.items()):
        # Freeze opponents at the start of the Eastern game day; no intraday ordering bias.
        fixed=dict(current)
        for g in daygames:
            ids=list(g['teams']);d1=[i for i in ids if i in known]
            if len(ids)!=2 or not d1:raise ValueError('Invalid teams')
            scores={i:g['teams'][i]['points'] for i in ids}
            if not all(finite(v) and v>=0 for v in scores.values()) or len(set(scores.values()))!=2:raise ValueError('Invalid final score')
            for i in d1:
                other=next(j for j in ids if j!=i);records[i][0 if scores[i]>scores[other] else 1]+=1
            if len(d1)==1:
                if g.get('opponent_classification')!='verified_non_d1':raise ValueError('Unverified opponent classification')
                i=d1[0];other=next(j for j in ids if j!=i)
                penalties[i]+=non_d1_penalty(scores[i]-scores[other]);non_d1[i]+=1
                continue
            p=possessions(list(g['teams'].values()))
            for i in ids:
                other=next(j for j in ids if j!=i)
                location=0 if g.get('neutral') else 1 if g['home']==i else -1
                raw_o=100*scores[i]/p;raw_d=100*scores[other]/p
                adjusted_o=raw_o-(fixed[other][1]-BASELINE)-location*HOME_NET_ADVANTAGE/2
                adjusted_d=raw_d-(fixed[other][0]-BASELINE)+location*HOME_NET_ADVANTAGE/2
                observations[i].append((adjusted_o,adjusted_d));schedules[i].append(fixed[other][0]-fixed[other][1])
                audit.append({'game_id':str(g['id']),'date':g['date'],'team_id':i,'opponent_id':other,'possessions':p,'opponent_pregame_offense':fixed[other][0],'opponent_pregame_defense':fixed[other][1],'adjusted_offense':adjusted_o,'adjusted_defense':adjusted_d})
        for i in known:current[i]=ratings(i)
    previous={t['team_id']:t for t in (previous or {}).get('teams',[])}
    rows=[]
    for i,t in known.items():
        o,d=current[i];n=len(observations[i]);r=reg[i]
        rows.append({'team_id':i,'slug':t['slug'],'name':r['short_name'],'logo':r.get('logo'),'conference':r.get('conference'),'preseason_rank':t['rank'],'average_preseason_rank':t['average_rank'],'source_ranks':t['source_ranks'],'rating':o-d-penalties[i], 'offensive_rating':o if n else None,'defensive_rating':d if n else None,'net_efficiency':o-d if n else None,'strength_of_schedule':sum(schedules[i])/n if n else None,'d1_games':n,'non_d1_games':non_d1[i],'preseason_weight':anchor_weight(n),'non_d1_penalty':penalties[i],'wins':records[i][0],'losses':records[i][1],'recent_form':(weighted_mean([a-b for a,b in observations[i][-7:]]) if n else None)})
    center=statistics.fmean(t['rating'] for t in rows);scale=statistics.pstdev(t['rating'] for t in rows) or 1.0
    for t in rows:t['strength_score']=50+10*(t['rating']-center)/scale
    rows.sort(key=lambda t:(-t['rating'],t['preseason_rank']))
    for i,t in enumerate(rows,1):
        t['rank']=i;p=previous.get(t['team_id']);t['rank_change']=p['rank']-i if p else 0
    for field,rank,reverse in [('offensive_rating','offense_rank',True),('defensive_rating','defense_rank',False),('strength_of_schedule','sos_rank',True)]:
        ranked=sorted([t for t in rows if t[field] is not None],key=lambda t:((-t[field] if reverse else t[field]),t['rank']))
        for i,t in enumerate(ranked,1):t[rank]=i
    output={'model':'betwise_cbb_strength_v1','season':seed['season'],'season_label':f"{seed['season']-1}–{str(seed['season'])[-2:]}",'updated_at':now.isoformat(),'status':'Preseason' if not audit else 'In season','games_evaluated':len(seen),'data_through':max(byday,default=None),'sources':seed['sources'],'preseason_frozen_at':seed['frozen_at'],'coverage':{'pending_games':len(ledger.get('pending_games',[]))},'teams':rows}
    if ledger.get('pending_games'):raise ValueError('Unverified completed games remain; retain previous published snapshot')
    return output,audit

def main():
    p=argparse.ArgumentParser();p.add_argument('--season',type=int,default=2027);args=p.parse_args()
    base=ROOT/'data/cbb';seed=json.loads((base/f'preseason/{args.season}.json').read_text());ledger=json.loads((base/f'strength-games/{args.season}.json').read_text());registry=json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams']
    now=datetime.now(timezone.utc);date=now.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    previous_dates=sorted(p for p in (base/f'strength-history/{args.season}').glob('*.json') if p.stem<date) if (base/f'strength-history/{args.season}').exists() else []
    previous=json.loads(previous_dates[-1].read_text()) if previous_dates else None
    out,audit=calculate(seed,ledger,registry,now,previous)
    save(base/'strength-rankings.json',out);save(base/f'strength-history/{args.season}/{date}.json',out);save(base/'strength-observations.json',{'season':args.season,'observations':audit})
    print(json.dumps({'teams':len(out['teams']),'status':out['status'],'games':out['games_evaluated'],'top_10':[t['name'] for t in out['teams'][:10]]}))
if __name__=='__main__':main()
