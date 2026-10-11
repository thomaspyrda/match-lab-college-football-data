#!/usr/bin/env python3
"""Independent opponent-normalized dominance pilot. Research only; no production writes.

Uses pregame opponent defensive allowed profiles, not v15 rankings/SOS.
Trains 2022-24, validates 2025, evaluates 2026. Advanced endpoint metrics only.
"""
import json, os, math, statistics, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'data/experiments/ond_pilot_2026.json'
KEY=os.environ['CFBD_API_KEY']
SEASONS=(2022,2023,2024,2025,2026)
FIELDS={
 'ppa':('ppa',), 'success_rate':('successRate',),
 'passing_ppa':('passingPlays','ppa'), 'passing_success':('passingPlays','successRate'),
 'rushing_ppa':('rushingPlays','ppa'), 'rushing_success':('rushingPlays','successRate'),
 'passing_explosiveness':('passingPlays','explosiveness'),
 'rushing_explosiveness':('rushingPlays','explosiveness'),
 'line_yards':('lineYards',), 'power_success':('powerSuccess',),
 'standard_down_success':('standardDowns','successRate'),
 'passing_down_success':('passingDowns','successRate'),
 'stuff_avoidance':('stuffRate',),
}
def api(route,**kwargs):
 url='https://api.collegefootballdata.com'+route+'?'+urllib.parse.urlencode(kwargs)
 req=urllib.request.Request(url,headers={'Authorization':'Bearer '+KEY,'Accept':'application/json','User-Agent':'BetWise-OND-research'})
 with urllib.request.urlopen(req,timeout=150) as f:return json.load(f)
def value(rec,path):
 v=rec.get('offense') or {}
 for p in path:
  if not isinstance(v,dict):return None
  v=v.get(p)
 try:return float(v) if v is not None else None
 except (ValueError,TypeError):return None
def fit(train):
 # small, interpretable ridge with opponent profile + home; chosen from training only
 n=len(train)
 x=[[1.0,r['opponent_allow'],r['home']] for r in train]
 y=[r['actual'] for r in train]
 import numpy as np
 x=np.array(x); y=np.array(y)
 penalty=np.diag([0.0,2.0,4.0])
 return np.linalg.solve(x.T@x+penalty,x.T@y).tolist()
def predict(coef,row):return coef[0]+coef[1]*row['opponent_allow']+coef[2]*row['home']
def error(rows,func):
 e=[r['actual']-func(r) for r in rows]
 return {'n':len(e),'rmse':round(math.sqrt(sum(z*z for z in e)/len(e)),5),'mae':round(sum(abs(z) for z in e)/len(e),5)} if e else None

allrows=[]
for yr in SEASONS:
 print('Fetching',yr,flush=True)
 games=api('/games',year=yr,seasonType='regular',division='fbs')
 advanced=api('/stats/game/advanced',year=yr,seasonType='regular',excludeGarbageTime='true')
 fbs={t['school'] for t in api('/teams/fbs',year=yr) if t.get('school')}-{ 'Sacramento State','North Dakota State' }
 bygame=defaultdict(dict)
 for rec in advanced:
  if rec.get('team') and rec.get('gameId') is not None:
   bygame[str(rec['gameId'])][rec['team']]=rec
 # Chronology must be based on game date, not API ordering.
 games=sorted([g for g in games if g.get('completed') or g.get('home_points') is not None or g.get('homePoints') is not None],key=lambda g:g.get('start_date') or g.get('startDate') or '')
 allowed=defaultdict(lambda:defaultdict(list))
 # Historical fallback baseline, used only as an uninformed prior.
 for g in games:
  gid=str(g.get('id') or g.get('game_id'))
  home=g.get('home_team') or g.get('homeTeam'); away=g.get('away_team') or g.get('awayTeam')
  paired=bygame.get(gid,{})
  if not home or not away or home not in fbs or away not in fbs or home not in paired or away not in paired:continue
  for offense,defense in ((home,away),(away,home)):
   for metric,path in FIELDS.items():
    actual=value(paired[offense],path)
    conceded=value(paired[defense],path)
    if actual is None:continue
    history=allowed[defense][metric]
    # 3-game shrink toward neutral zero in normalized z-space, with no future leakage.
    # Shrinkage is learned indirectly in ridge, not from v15 team ranks.
    # Opponent historical allowed statistic measures what previous opposing offenses achieved.
    prior=statistics.fmean(history) if history else None
    allrows.append({'season':yr,'game_id':gid,'team':offense,'opponent':defense,'metric':metric,'actual':-actual if metric=='stuff_avoidance' else actual,'prior_allowed':(-prior if metric=='stuff_avoidance' else prior) if prior is not None else None,'prior_games':len(history),'home':1 if offense==home else 0})
  # At end of game, update both defenses using the other team's offense values.
  for defense,offense in ((home,away),(away,home)):
   for metric,path in FIELDS.items():
    val=value(paired[offense],path)
    if val is not None:allowed[defense][metric].append(val)

calib=json.loads((ROOT/'data/experiments/sd_to_sd_calibration_v14.json').read_text())['metrics']
metrics={}
miami=[]
texas_tech=[]
fbs_2026=[]
for metric in FIELDS:
 samples=[r.copy() for r in allrows if r['metric']==metric]
 train=[r for r in samples if r['season']<=2024]
 if len(train)<100:continue
 mu=statistics.fmean(r['actual'] for r in train)
 sd=statistics.pstdev(r['actual'] for r in train) or 1
 # The prior-allowed baseline is neutral when no earlier opponent sample exists.
 for r in samples:
  prior=mu if r['prior_allowed'] is None else r['prior_allowed']
  # Explicit shrinkage for sparse opponent profiles.
  r['opponent_allow']=(r['prior_games']*prior+3*mu)/(r['prior_games']+3)
  r['actual']=(r['actual']-mu)/sd
  r['opponent_allow']=(r['opponent_allow']-mu)/sd
 train=[r for r in samples if r['season']<=2024]
 val=[r for r in samples if r['season']==2025]
 test=[r for r in samples if r['season']==2026]
 c=fit(train)
 residual_sigma=statistics.pstdev([r['actual']-predict(c,r) for r in val]) or 1.0
 k=calib.get(metric,{}).get('selected_coefficient',0.2)
 # V15-shaped comparator uses same opponent information and historical coefficient,
 # but it is NOT the v15 production ranking model.
 baselines={'neutral':lambda r:0,'v15_coefficient_proxy':lambda r:k*r['opponent_allow'],'ond_ridge':lambda r:predict(c,r)}
 metrics[metric]={'trained':len(train),'coefficient':c,'v15_proxy_k':k,'validation_residual_sigma':round(residual_sigma,5),'validation_2025':{n:error(val,f) for n,f in baselines.items()},'test_2026':{n:error(test,f) for n,f in baselines.items()}}
 for r in test:
  actual=r['actual'];expected=predict(c,r)
  if r['season']==2026:
   fbs_2026.append({'team':r['team'],'opponent':r['opponent'],'game_id':r['game_id'],'metric':metric,'dominance_residual_sd':round((actual-expected)/residual_sigma,3)})
  if r['team'] not in ('Miami','Texas Tech'):continue
  actual=r['actual'];expected=predict(c,r)
  target=miami if r['team']=='Miami' else texas_tech
  target.append({'game_id':r['game_id'],'opponent':r['opponent'],'metric':metric,'observed_z':round(actual,3),'expected_average_fbs_z':round(expected,3),'dominance_residual_z':round(actual-expected,3),'dominance_residual_sd':round((actual-expected)/residual_sigma,3),'opponent_prior_games':r['prior_games']})
summary={}
for period in ('validation_2025','test_2026'):
 complete=[v[period] for v in metrics.values() if v[period]['ond_ridge'] and v[period]['v15_coefficient_proxy']]
 summary[period]={'metric_count':len(complete),'mean_metric_rmse':{n:round(statistics.fmean(v[n]['rmse'] for v in complete),5) for n in ('neutral','v15_coefficient_proxy','ond_ridge')},'ond_better_than_proxy_metrics':sum(v['ond_ridge']['rmse']<v['v15_coefficient_proxy']['rmse'] for v in complete)}
payload={'schema':'ond-independent-pilot-v1','train':[2022,2023,2024],'validation':2025,'test':2026,'features':'Pregame opponent defensive allowance history, shrunk toward FBS training mean; home-field flag. No separate SOS.','limitations':'Pilot covers 13 advanced-endpoint metrics rather than complete 38/41; 2026 is partial; games are used in team-season chronological order; benchmark uses v15 coefficients on independent prior allowance proxy, not exact production v15; raw z-scores use training FBS game SD; the additional residual SD scores use 2025 holdout prediction-error SD; no external venue or roster controls.','results':summary,'metrics':metrics,'miami_2026':miami,'texas_tech_2026':texas_tech,'fbs_2026_dominance':fbs_2026}
DEST.parent.mkdir(parents=True,exist_ok=True)
DEST.write_text(json.dumps(payload,indent=2)+'\n')
print(json.dumps({'results':summary,'miami_rows':len(miami)},indent=2))
