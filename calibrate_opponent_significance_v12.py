#!/usr/bin/env python3
"""V12 opponent-significance calibration.

Train on 2022-2024 FBS-vs-FBS games. Hold out 2025 for validation.
Controls for the performing team's own leave-one-game-out unit baseline before
estimating how opponent quality changes the significance of a game performance.
"""
import json, math, os, statistics, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path
from experiment_dominance_v8 import METRICS, canon, metric_row

ROOT=Path(__file__).resolve().parent
TRAIN=(2022,2023,2024)
VALIDATE=(2025,)
OUT=ROOT/"data"/"experiments"/"opponent_significance_calibration_v12.json"
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret required")

def api(path,**params):
    url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
    with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)

def mean(xs):
    xs=[x for x in xs if x is not None]
    return statistics.fmean(xs) if xs else None

def significance(q,alpha=2.0):
    if not q:return 0.0
    return math.copysign(math.log1p(alpha*abs(q))/math.log1p(alpha),q)

def metric_row_v12(row,points):
    mr=metric_row(row,points)
    if mr.get("finishing") is None:
        o=row.get("offense") or {}
        opp=o.get("totalOpportunities")
        try: opp=float(opp) if opp is not None else None
        except: opp=None
        try: pts=float(points) if points is not None else None
        except: pts=None
        if opp and pts is not None: mr["finishing"]=pts/opp
    return mr

def season_rows(year):
    games=api("/games",year=year,seasonType="regular")
    adv=api("/stats/game/advanced",year=year,seasonType="regular",excludeGarbageTime="true")
    by_gid=defaultdict(dict)
    for row in adv:
        if row.get("team"):by_gid[str(row.get("gameId"))][canon(row["team"])]=row
    fbs={canon(x["school"]) for x in api("/teams/fbs",year=year) if x.get("school")}
    obs=[]
    for g in games:
        if not g.get("completed",True):continue
        gid=str(g.get("id")); h=canon(g.get("homeTeam")); a=canon(g.get("awayTeam")); rows=by_gid.get(gid,{})
        if h not in fbs or a not in fbs or h not in rows or a not in rows:continue
        hm=metric_row_v12(rows[h],g.get("homePoints")); am=metric_row_v12(rows[a],g.get("awayPoints"))
        obs.extend([(gid,h,a,hm),(gid,a,h,am)])
    return obs

def residual_pairs(obs,m):
    vals=[r[3][m] for r in obs if r[3].get(m) is not None]
    if len(vals)<20:return []
    mu=statistics.fmean(vals); sd=statistics.pstdev(vals) or 1.0
    rows=[(gid,t,o,(mr[m]-mu)/sd) for gid,t,o,mr in obs if mr.get(m) is not None]
    produced=defaultdict(list); defended=defaultdict(list)
    for gid,t,o,z in rows:
        produced[t].append((gid,z))
        defended[o].append((gid,-z))
    pairs=[]
    for gid,t,o,z in rows:
        own_off=mean(v for g,v in produced[t] if g!=gid)
        opp_def=mean(v for g,v in defended[o] if g!=gid)
        own_def=mean(v for g,v in defended[t] if g!=gid)
        opp_off=mean(v for g,v in produced[o] if g!=gid)
        if own_off is not None and opp_def is not None:
            pairs.append(("offense",significance(opp_def),z-own_off,opp_def,z,own_off))
        if own_def is not None and opp_off is not None:
            pairs.append(("defense",significance(opp_off),(-z)-own_def,opp_off,-z,own_def))
    return pairs

def fit_lambda(pairs):
    # own residual ~= -lambda * opponent significance
    if len(pairs)<50:return 0.0
    xs=[p[1] for p in pairs]; ys=[p[2] for p in pairs]
    den=sum(x*x for x in xs)
    if not den:return 0.0
    lam=-sum(x*y for x,y in zip(xs,ys))/den
    return max(0.0,min(2.5,lam))

def rmse(pairs,lam):
    if not pairs:return None
    errs=[(p[4]+lam*p[1])-p[5] for p in pairs]
    return math.sqrt(statistics.fmean(e*e for e in errs))

def bands(pairs,lam):
    defs=[("weak",-99,-1.0),("below_average",-1.0,-0.5),("average",-0.5,0.5),("strong",0.5,1.0),("elite",1.0,1.5),("exceptional",1.5,99)]
    out={}
    for name,lo,hi in defs:
        ps=[p for p in pairs if lo<=p[3]<hi]
        out[name]={"samples":len(ps),"mean_opponent_sd":round(mean(p[3] for p in ps),3) if ps else None,
                   "mean_adjustment_sd":round(mean(lam*p[1] for p in ps),3) if ps else None}
    return out

train_obs={y:season_rows(y) for y in TRAIN}
val_obs={y:season_rows(y) for y in VALIDATE}
metrics={}
for m in METRICS:
    tr=[]; va=[]
    for y in TRAIN:tr+=residual_pairs(train_obs[y],m)
    for y in VALIDATE:va+=residual_pairs(val_obs[y],m)
    lam=fit_lambda(tr)
    metrics[m]={
      "lambda":round(lam,6),"training_samples":len(tr),"validation_samples":len(va),
      "validation_rmse_raw":round(rmse(va,0.0),6) if va else None,
      "validation_rmse_v12":round(rmse(va,lam),6) if va else None,
      "validation_rmse_unit_linear":round(rmse(va,1.0),6) if va else None,
      "validation_opponent_bands":bands(va,lam)
    }
payload={
 "schema_version":"opponent-significance-v12.0",
 "training_seasons":list(TRAIN),"validation_seasons":list(VALIDATE),
 "curve":{"type":"signed_log","alpha":2.0,"anchor":"+/-1 opponent SD maps to +/-1 significance unit"},
 "method":"leave-one-game-out own-unit residual regressed on signed-log opponent unit quality; coefficient fit through origin after controlling own unit baseline; 2025 held out",
 "finishing_fallback":"offense.pointsPerOpportunity when present; otherwise team points / offense.totalOpportunities",
 "metrics":metrics}
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text(json.dumps(payload,indent=2)+"\n")
print(json.dumps(payload,indent=2))
