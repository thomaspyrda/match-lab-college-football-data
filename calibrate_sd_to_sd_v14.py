#!/usr/bin/env python3
"""Calibrate v14 direct SD-to-SD opponent adjustment.

Tests the literal hypothesis that one SD of opposing-unit strength warrants one
SD of game-performance adjustment, alongside coefficients estimated on 2022-24.
2025 is held out. Opponent quality stays linear in the same FBS SD space.
"""
import json, os, statistics, urllib.parse, urllib.request, math
from collections import defaultdict
from pathlib import Path
from experiment_dominance_v12 import METRICS, canon, metric_row
ROOT=Path(__file__).resolve().parent
TRAIN=(2022,2023,2024); VALIDATE=(2025,)
OUT=ROOT/"data"/"experiments"/"sd_to_sd_calibration_v14.json"
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret required")
def api(path,**params):
    url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
    with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
def mean(xs):
    xs=[x for x in xs if x is not None]; return statistics.fmean(xs) if xs else None
def rows(year):
    games=api("/games",year=year,seasonType="regular"); adv=api("/stats/game/advanced",year=year,seasonType="regular",excludeGarbageTime="true")
    by=defaultdict(dict)
    for r in adv:
        if r.get("team"):by[str(r.get("gameId"))][canon(r["team"])]=r
    fbs={canon(x["school"]) for x in api("/teams/fbs",year=year) if x.get("school")}; out=[]
    for g in games:
        gid=str(g.get("id")); h=canon(g.get("homeTeam")); a=canon(g.get("awayTeam")); rr=by.get(gid,{})
        if not g.get("completed",True) or h not in fbs or a not in fbs or h not in rr or a not in rr:continue
        out.extend([(gid,h,a,metric_row(rr[h],g.get("homePoints"))),(gid,a,h,metric_row(rr[a],g.get("awayPoints")))])
    return out
def pairs(obs,m):
    vals=[x[3].get(m) for x in obs if x[3].get(m) is not None]
    if len(vals)<20:return []
    mu=statistics.fmean(vals); sd=statistics.pstdev(vals) or 1
    rr=[(gid,t,o,(mr[m]-mu)/sd) for gid,t,o,mr in obs if mr.get(m) is not None]
    prod=defaultdict(list); deff=defaultdict(list)
    for gid,t,o,z in rr:prod[t].append((gid,z));deff[o].append((gid,-z))
    out=[]
    for gid,t,o,z in rr:
        ob=mean(v for g,v in prod[t] if g!=gid); od=mean(v for g,v in deff[o] if g!=gid)
        db=mean(v for g,v in deff[t] if g!=gid); oo=mean(v for g,v in prod[o] if g!=gid)
        if ob is not None and od is not None:out.append((z-ob,od,z,ob))
        if db is not None and oo is not None:out.append(((-z)-db,oo,-z,db))
    return out
def fit(ps):
    den=sum(q*q for _,q,_,_ in ps)
    return max(0,min(1.5,-sum(q*r for r,q,_,_ in ps)/den)) if den else 0
def rmse(ps,k):
    return math.sqrt(statistics.fmean(((raw+k*q)-base)**2 for _,q,raw,base in ps)) if ps else None
tr={y:rows(y) for y in TRAIN}; va={y:rows(y) for y in VALIDATE}; metrics={}
for m in METRICS:
    tp=sum((pairs(tr[y],m) for y in TRAIN),[]); vp=sum((pairs(va[y],m) for y in VALIDATE),[])
    k=fit(tp); candidates={"0.0":rmse(vp,0),"fitted":rmse(vp,k),"1.0":rmse(vp,1)}
    # Choose between direct 1:1 and fitted coefficient on held-out validation; raw is diagnostic, not an opponent-adjusted model.
    selected=1.0 if candidates["1.0"] is not None and candidates["1.0"]<=candidates["fitted"] else k
    metrics[m]={"fitted_coefficient":round(k,6),"selected_coefficient":round(selected,6),"training_samples":len(tp),"validation_samples":len(vp),
      "validation_rmse_raw":round(candidates["0.0"],6) if candidates["0.0"] else None,
      "validation_rmse_fitted":round(candidates["fitted"],6) if candidates["fitted"] else None,
      "validation_rmse_1_to_1":round(candidates["1.0"],6) if candidates["1.0"] else None}
payload={"schema_version":"sd-to-sd-v14.0","training_seasons":list(TRAIN),"validation_seasons":list(VALIDATE),
 "formula":"adjusted game SD = raw game-performance SD + coefficient * corresponding opponent-unit SD",
 "selection":"compare historically fitted coefficient with literal 1:1 on held-out 2025; raw/no adjustment retained as diagnostic",
 "metrics":metrics}
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2)+"\n");print(json.dumps(payload,indent=2))
