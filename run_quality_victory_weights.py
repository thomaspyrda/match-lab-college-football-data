#!/usr/bin/env python3
"""Research-only quality victories sensitivity 0/2.5/5/7.5%; no production changes."""
import json, pathlib, os, math, statistics, collections, urllib.request
R=pathlib.Path(__file__).resolve().parent
# Recreate week-start opponent ratings and CPC evidence exactly from previous test.
source=(R/'run_proven_competition_research.py').read_text()
ns={'__file__':str(R/'run_proven_competition_research.py')}
exec(compile(source.split('def score(t,wcpc,wmov):',1)[0],'<cpc-core>','exec'),ns)
baseline=ns['baseline'];eligible=ns['eligible'];cpc_z=ns['z'];games=ns['games'];spread=ns['spread'];pre=ns['pre']
ratings={t:float(pre[t]['score']) if t in pre else 45.0 for t in eligible}
qv=collections.defaultdict(list);detail=collections.defaultdict(list)
for week in range(1,7):
 snapshot=ratings.copy();update=collections.defaultdict(list)
 matches=[g for g in games if int(g.get('week') or 0)==week and g.get('result') and g.get('home') in eligible and g.get('away') in eligible]
 for g in matches:
  h,a=g['home'],g['away'];margin=float(g['result']['home_points'])-float(g['result']['away_points'])
  expected=2.5+.22*(snapshot[h]-snapshot[a]);err=max(-25,min(25,margin-expected))
  update[h].append(.14*err);update[a].append(-.14*err)
  # Pregame win probability from frozen pregame strength, NOT closing spread.
  ph=1/(1+math.exp(-max(-10,min(10,expected/11.0))))
  for t,o,won,pwin in ((h,a,margin>0,ph),(a,h,margin<0,1-ph)):
   opponent_rank=1+sum(snapshot[x]>snapshot[o] for x in eligible)
   quality=1/(1+math.exp((opponent_rank-40)/14))
   # Quality result is a win surprise, scaled to opponent quality; non-wins
   # at strong opposition are moderated rather than automatically rewarded.
   residual=(int(won)-pwin)*quality
   qv[t].append(residual)
   detail[t].append({'week':week,'opponent':o,'pregame_opponent_rank_proxy':opponent_rank,'win':won,'pregame_win_probability':round(pwin,3),'quality_result':round(residual,4)})
 for t,updates in update.items():ratings[t]+=sum(updates)
raw={t:(sum(qv[t])/(len(qv[t])+4) if qv[t] else None) for t in eligible}
vals=[v for v in raw.values() if v is not None];mu=statistics.fmean(vals);sd=statistics.pstdev(vals)
qz={t:(raw[t]-mu)/sd if raw[t] is not None and sd>0 else None for t in eligible}
runs={}
for w in [0,.025,.05,.075]:
 vals={}
 for t in eligible:
  b=baseline[t]['baseline_sd'];mov=baseline[t]['mov_sd'];cpc=cpc_z[t];quality=qz[t]
  vals[t]=(.85-w)*b+.10*(mov if mov is not None else b)+.05*(cpc if cpc is not None else b)+w*(quality if quality is not None else b)
 order=sorted(eligible,key=lambda t:(-vals[t],t))
 runs[str(w)]={'weights':{'baseline':round(.85-w,3),'mov':.1,'cpc':.05,'quality':w},'top50':order[:50],'ranks':{t:i+1 for i,t in enumerate(order)}}
focus=['Oklahoma','Texas','New Mexico','Georgia','Miami','Notre Dame','Oregon','SMU','Alabama','Ohio State','Navy','Rutgers']
report={'status':'completed research only','through_week':6,'formula':'(0.85-quality_weight)*prior_strength + 0.10 MOV + 0.05 CPC + quality_weight*QVCP','quality_definition':'Game win surprise (win - frozen week-start model win probability) multiplied by continuous frozen pregame opponent quality; reliability-shrunk 4 games and cross-team z standardized','quality_rating_source':'CPC provisional week-start preseason plus margin residual proxy (not original model unit ratings)','note':'Baseline already includes a quality-results component (QRR ~15% inside original research model). This sensitivity test has not surgically removed QRR; quality win double-count risk remains. Not suitable for production adoption.',
 'limitations':['Existing QRR inside baseline not independently removed; overlapping result reward','No held-out games; rankings sensitivity only','Model expectation win-probability slope 11 points is provisional and uncalibrated','Pregame strength proxy is not exact frozen primary model','Market spread records in MOV/CPC are not kickoff-close certified'],
 'models':{k:{'weights':v['weights'],'top50':v['top50']} for k,v in runs.items()},
 'focus':[{'team':t,'quality_z':round(qz[t],3) if qz[t] is not None else None,'ranks':{k:v['ranks'][t] for k,v in runs.items()},'games':detail[t]} for t in focus]}
out=R/'data/experiments/quality_victory_weight_comparison_2026.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'focus':[{'team':r['team'],'quality_z':r['quality_z'],'ranks':r['ranks']} for r in report['focus']],'top25':{k:v['top50'][:25] for k,v in report['models'].items()}},indent=2))

# Execute isolated test.
