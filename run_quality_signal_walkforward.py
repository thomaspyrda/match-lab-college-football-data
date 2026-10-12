#!/usr/bin/env python3
"""Walk-forward incremental value of CPC and quality victories over game market spreads.
Research only. No future game inputs in features; no fitted weights on holdout.
"""
import os,json,math,pathlib,urllib.request,urllib.parse,statistics,collections
R=pathlib.Path(__file__).resolve().parent
YEARS=[2024,2025,2026]
API=os.environ['CFBD_API_KEY']
def api(path,**kw):
 req=urllib.request.Request('https://api.collegefootballdata.com'+path+'?'+urllib.parse.urlencode(kw),headers={'Authorization':'Bearer '+API,'Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=120) as f:return json.load(f)
pre=json.loads((R/'data/preseason/2026.json').read_text())['teams']
predictions=[];year_reports={};coverage={}
for year in YEARS:
 hist=json.loads((R/f'data/historical/{year}.json').read_text())['games']
 lines=api('/lines',year=year,seasonType='regular')
 sp={}
 for item in lines:
  providers=sorted((p for p in item.get('lines',[]) if p.get('spread') is not None),
      key=lambda p:(0 if 'consensus' in str(p.get('provider','')).lower() else 1,0 if 'draftkings' in str(p.get('provider','')).lower() else 1,str(p.get('provider',''))))
  if providers:
   try:sp[str(item['id'])]=float(providers[0]['spread'])
   except (KeyError,TypeError,ValueError):pass
 completed=[g for g in hist if g.get('result') and 1<=int(g.get('week') or 0)<=15 and g.get('home') and g.get('away')]
 # Unknown early-season teams get a neutral start; 2026 has independently
 # published preseason priors. Ratings here are a pregame proxy, not the main model.
 teams=set(t for g in completed for t in (g['home'],g['away']))
 ratings={t:(float(pre[t]['score'])-50)*.15 if year==2026 and t in pre else 0. for t in teams}
 histories=collections.defaultdict(list)
 for week in sorted(set(int(g['week']) for g in completed)):
  this_week=[g for g in completed if int(g['week'])==week]
  snap=ratings.copy()
  strength_order=sorted(teams,key=lambda t:(-snap[t],t))
  opp_rank={t:i+1 for i,t in enumerate(strength_order)}
  pending=collections.defaultdict(list)
  for g in this_week:
   h,a=g['home'],g['away']
   result=g['result'];home_margin=float(result['home_points'])-float(result['away_points'])
   expected=2.5+snap[h]-snap[a]
   pending[h].append(.07*max(-28,min(28,home_margin-expected)))
   pending[a].append(-.07*max(-28,min(28,home_margin-expected)))
   bookspread=sp.get(str(g['game_id']))
   if bookspread is None:continue
   if week>=4:
    # Only past games enter the aggregates.
    def aggregate(t,kind):
     games=histories[t];num=len(games)
     return sum(x[kind] for x in games)/(num+4) if num else 0
    hm=aggregate(h,'mov');am=aggregate(a,'mov')
    hc=aggregate(h,'cpc');ac=aggregate(a,'cpc')
    hq=aggregate(h,'qv');aq=aggregate(a,'qv')
    # Regularization of pre-game adjustments, measured in scoring-margin pts.
    # No overlapping quality results in base or CPC: QV is the only result surprise.
    arms={
      'market':-bookspread,
      'mov':-bookspread+.20*(hm-am),
      'mov_cpc':-bookspread+.15*(hm-am)+.15*(hc-ac),
      'mov_cpc_qv':-bookspread+.15*(hm-am)+.10*(hc-ac)+3*(hq-aq)
    }
    for name,pred in arms.items():
     predictions.append({'year':year,'week':week,'game_id':str(g['game_id']),'arm':name,'pred':pred,'actual':home_margin,'spread':bookspread})
   # Games already completed at current week are only added after ALL week predictions.
  for g in this_week:
   h,a=g['home'],g['away'];r=g['result'];home_margin=float(r['home_points'])-float(r['away_points'])
   s=sp.get(str(g['game_id']))
   if s is None:continue
   resid=max(-35,min(35,home_margin+s))
   for t,opp,rr,won in ((h,a,resid,home_margin>0),(a,h,-resid,home_margin<0)):
    rk=opp_rank[opp]
    q=1/(1+math.exp((rk-55)/17))
    cpc=rr*((.25+1.05*q) if rr>=0 else (.75+.50*(1-q)))
    # No win-probability modeled with the actual result or future data.
    # Here the market spread gives a strictly pregame result expectation.
    team_line=s if t==h else -s
    pwin=1/(1+math.exp(-max(-10,min(10,-team_line/11))))
    qv=(int(won)-pwin)*(1/(1+math.exp((rk-40)/14)))
    histories[t].append({'mov':rr,'cpc':cpc,'qv':qv})
  for t,deltas in pending.items():ratings[t]+=sum(deltas)
 coverage[year]={'games_found':len(completed),'games_with_market_lines':sum(str(g['game_id']) in sp for g in completed),'evaluated_games':len(set(x['game_id'] for x in predictions if x['year']==year))}
by=collections.defaultdict(list)
for p in predictions:by[p['arm']].append(p)
def scores(xs):
 n=len(xs)
 return {'n':n,'mae':round(sum(abs(x['pred']-x['actual']) for x in xs)/n,4),
  'rmse':round(math.sqrt(sum((x['pred']-x['actual'])**2 for x in xs)/n),4),
  'winner_accuracy':round(sum((x['pred']>=0)==(x['actual']>0) for x in xs)/n,4),
  'error_bias':round(sum(x['pred']-x['actual'] for x in xs)/n,4)} if n else None
report={'status':'completed_incremental_research','years':YEARS,'coverage':coverage,'results':{k:scores(v) for k,v in by.items()},
 'per_year':{year:{k:scores([p for p in xs if p['year']==year]) for k,xs in by.items()} for year in YEARS},
 'method':'Out-of-week predictions using only prior-week market residuals and frozen quality-proxy opponent ranks. Market line used as predictor; additions are past MOV residual, CPC quality-weighted residual, or de-duplicated win-surprise quality residual. No current-week results are used before predicting.',
 'limitations':['NOT a rerun of original v15 full-metric baseline: this tests incremental historical signal beyond available market lines','No guarantee /lines snapshots are exact kickoff closes','2014-2025 offseason preseason priors unavailable here, hence zero initial rating outside 2026','Opponent quality proxy is prior-week margin-updated rating, not original frozen unit model','Coefficients are provisional, not optimized or calibrated on a training set','2026 results only through week 6 in this comparison by date; earlier years through week 15','No injuries or roster changes'],
 'recommendation_rule':'Only adopt feature if it reduces held-out MAE/RMSE across multiple seasons without harming coverage or creating redundancy.'}
if not by or len(by['market'])<300:raise RuntimeError('Insufficient evaluation market line coverage '+str(coverage))
p=R/'data/experiments/quality_signal_walkforward_2024_2026.json'
p.parent.mkdir(exist_ok=True,parents=True);p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
