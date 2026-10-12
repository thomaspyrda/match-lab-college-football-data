#!/usr/bin/env python3
"""Research-only: weak-opponent evidence limits and proven-competition consistency.
No production ranks are modified. Uses frozen WEEK-START strength proxy (preseason + earlier results).
"""
import json,os,pathlib,collections,statistics,math,urllib.request
R=pathlib.Path(__file__).resolve().parent
old=json.loads((R/'data/experiments/closing_mov_10pct_pregame_comparison_2026.json').read_text())
baseline={r['team']:r for r in old['rankings']}
pre=json.loads((R/'data/preseason/2026.json').read_text())['teams']
games=json.loads((R/'data/historical/2026.json').read_text())['games']
eligible=set(baseline)
ranks={t:float(pre[t]['score']) if t in pre else 45.0 for t in eligible}
key=os.environ['CFBD_API_KEY']
req=urllib.request.Request('https://api.collegefootballdata.com/lines?year=2026&seasonType=regular',headers={'Authorization':'Bearer '+key,'Accept':'application/json'})
with urllib.request.urlopen(req,timeout=120) as f:lines=json.load(f)
spread={}
for obj in lines:
 pp=sorted((v for v in obj.get('lines',[]) if v.get('spread') is not None),key=lambda v:(0 if 'consensus' in str(v.get('provider','')).lower() else 1,0 if 'draftkings' in str(v.get('provider','')).lower() else 1,str(v.get('provider',''))))
 if pp:
  try:spread[str(obj['id'])]=float(pp[0]['spread'])
  except (KeyError,ValueError,TypeError):pass
processed=collections.defaultdict(list)
quality=collections.defaultdict(list)
audit=[]
# Week-start snapshot prevents within-week game ordering from changing quality tiers.
for week in range(1,7):
 matches=[g for g in games if int(g.get('week') or 0)==week and g.get('result') and g.get('home') in eligible and g.get('away') in eligible]
 snapshot=dict(ranks)
 updated=collections.defaultdict(list)
 for g in matches:
  h,a=g['home'],g['away']; result=g['result']
  hm=float(result['home_points'])-float(result['away_points'])
  expected=2.5+.22*(snapshot[h]-snapshot[a])
  error=max(-25,min(25,hm-expected))
  updated[h].append(.14*error);updated[a].append(-.14*error)
  sp=spread.get(str(g['game_id']))
  if sp is None:continue
  resid=max(-35,min(35,hm+sp))
  for t,o,r in ((h,a,resid),(a,h,-resid)):
   # Relative frozen, pregame strength rank, converted to a smooth quality factor.
   opp_rank=1+sum(1 for x in eligible if snapshot[x]>snapshot[o])
   q=1/(1+math.exp((opp_rank-55)/17))
   # Strong-opponent positive evidence expands. Weak-opponent positive residuals
   # are bounded; weak-opponent negative residuals have moderate amplification.
   positive_factor=.25+1.05*q
   negative_factor=.75+.50*(1-q)
   adjusted=r*(positive_factor if r>=0 else negative_factor)
   quality[t].append(adjusted)
   processed[t].append({'week':week,'opponent':o,'pregame_opponent_rank_proxy':opp_rank,
     'residual':round(r,2),'quality_weighted_residual':round(adjusted,2),
     'positive_factor':round(positive_factor,3),'negative_factor':round(negative_factor,3),
     'outcome':'W' if (hm if t==h else -hm)>0 else 'L'})
   audit.append((t,o))
 for t,up in updated.items():ranks[t]+=sum(up)
raw={t:(sum(quality[t])/(len(quality[t])+4) if quality[t] else None) for t in eligible}
valid=[v for v in raw.values() if v is not None];mu=statistics.fmean(valid);sd=statistics.pstdev(valid)
z={t:((raw[t]-mu)/sd if raw[t] is not None and sd else None) for t in eligible}
def score(t,wcpc,wmov):
 b=baseline[t]['baseline_sd'];mv=baseline[t]['mov_sd']
 # The 10% MOV arm matches the persisted experimental control.
 return (1-wcpc-wmov)*b + wmov*(mv if mv is not None else b)+wcpc*(z[t] if z[t] is not None else b)
def ranks_for(wcpc,wmov):
 ordered=sorted(eligible,key=lambda t:(-score(t,wcpc,wmov),t))
 return ordered,{t:i+1 for i,t in enumerate(ordered)}
runs={}
for label,wcpc,wmov in [('baseline',0,0),('separate_mov_10pct',0,.1),('cpc_only_5pct',.05,0),('mov_10pct_plus_cpc_5pct',.05,.1),('mov_10pct_plus_cpc_10pct',.10,.1)]:
 ordered,rr=ranks_for(wcpc,wmov)
 runs[label]={'weights':{'baseline':round(1-wcpc-wmov,2),'mov':wmov,'cpc':wcpc},'top25':ordered[:25],'ranks':rr}
focus=['New Mexico','SMU','Oklahoma','Texas','Georgia','Ohio State','Miami','Notre Dame','Oregon','Navy','Rutgers','Alabama']
report={'model':'continuous high-competition proof and weak-schedule capped upside','status':'research_only',
 'through_week':6,'eligible_lines':len(audit)//2,
 'strength_proxy':'Frozen week-start ranks seeded by the independent consensus preseason score; previous weeks updated using capped actual-margin residual vs 2.5 + 0.22*preseason-score gap. This is an Elo-like research proxy, NOT the original model frozen-unit rating.',
 'cpc':'Signed spread margin surprise x continuous opponent-quality modifier: positive credit 0.25x (weak) to 1.30x (elite); negative 0.75x (elite) to 1.25x (weak). Four-game shrinkage then centered SD normalization.',
 'important_limitations':['Strength quality is a provisional separate pregame proxy, not the production model historical strength','CFBD lines may not be certified at kickoff close','Weights/factors are hypotheses, not calibrated by out-of-sample forecasting','Quality and market MOV share residual information; combined arms can double-count','Higher final relative rank does not prove a stronger absolute rating'],
 'models':{k:{'weights':v['weights'],'top25':v['top25']} for k,v in runs.items()},
 'focus':[{'team':t,'games_with_lines':len(quality[t]),'cpc_z':round(z[t],3) if z[t] is not None else None,
 'ranks':{name:v['ranks'][t] for name,v in runs.items()},'game_breakdown':processed[t]} for t in focus],
 'largest_changes':sorted([{'team':t,'baseline_rank':runs['baseline']['ranks'][t],
  'proposed_rank':runs['mov_10pct_plus_cpc_5pct']['ranks'][t],
  'change':runs['baseline']['ranks'][t]-runs['mov_10pct_plus_cpc_5pct']['ranks'][t]} for t in eligible],key=lambda x:abs(x['change']),reverse=True)[:30],
 'weak_opponent_checks':{'positive_factor_at_rank_120':round(.25+1.05/(1+math.exp((120-55)/17)),3),
  'negative_factor_at_rank_120':round(.75+.50*(1-1/(1+math.exp((120-55)/17))),3),
  'positive_factor_at_rank_10':round(.25+1.05/(1+math.exp((10-55)/17)),3),
  'negative_factor_at_rank_10':round(.75+.50*(1-1/(1+math.exp((10-55)/17))),3)}}
p=R/'data/experiments/proven_competition_cpc_2026.json'
p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'games':len(audit)//2,'focus':[{k:v for k,v in x.items() if k!='game_breakdown'} for x in report['focus']],'checks':report['weak_opponent_checks']},indent=2))

# Research execution trigger.
