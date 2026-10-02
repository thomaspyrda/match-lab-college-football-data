#!/usr/bin/env python3
"""Calibrate v13 asymmetric performance x opponent-difficulty interaction.

2022-2024 train; 2025 held out. Candidate maximum modifier strengths are chosen
only from held-out 2025 error after controlling each team's leave-one-game-out
baseline. No 2026 rankings participate in selection.
"""
import json, math, os, statistics, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path
from experiment_dominance_v12 import METRICS, canon, metric_row

ROOT=Path(__file__).resolve().parent
TRAIN=(2022,2023,2024); VALIDATE=(2025,)
CANDIDATES=(0.15,0.20,0.25,0.30,0.35)
OUT=ROOT/"data"/"experiments"/"opponent_interaction_calibration_v13.json"
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret required")

def api(path,**params):
    url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
    with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)
def mean(xs):
    xs=[x for x in xs if x is not None]; return statistics.fmean(xs) if xs else None
def sig(q,alpha=2.0):
    if not q:return 0.0
    return math.copysign(math.log1p(alpha*abs(q))/math.log1p(alpha),q)
def modifier(q,strength):
    # +/-1 opponent SD maps to 1 +/- strength; cap prevents unstable extremes.
    return max(0.55,min(1.45,1.0+strength*sig(q)))
def adjust(p,q,strength):
    m=modifier(q,strength)
    return p*m if p>=0 else p/m

def rows(year):
    games=api("/games",year=year,seasonType="regular")
    adv=api("/stats/game/advanced",year=year,seasonType="regular",excludeGarbageTime="true")
    by=defaultdict(dict)
    for r in adv:
        if r.get("team"):by[str(r.get("gameId"))][canon(r["team"])]=r
    fbs={canon(x["school"]) for x in api("/teams/fbs",year=year) if x.get("school")}
    out=[]
    for g in games:
        gid=str(g.get("id")); h=canon(g.get("homeTeam")); a=canon(g.get("awayTeam")); rr=by.get(gid,{})
        if not g.get("completed",True) or h not in fbs or a not in fbs or h not in rr or a not in rr:continue
        hm=metric_row(rr[h],g.get("homePoints")); am=metric_row(rr[a],g.get("awayPoints"))
        out.extend([(gid,h,a,hm),(gid,a,h,am)])
    return out

def cases(obs,m):
    vals=[x[3].get(m) for x in obs if x[3].get(m) is not None]
    if len(vals)<20:return []
    mu=statistics.fmean(vals); sd=statistics.pstdev(vals) or 1
    rr=[(gid,t,o,(mr[m]-mu)/sd) for gid,t,o,mr in obs if mr.get(m) is not None]
    prod=defaultdict(list); deff=defaultdict(list)
    for gid,t,o,z in rr: prod[t].append((gid,z)); deff[o].append((gid,-z))
    out=[]
    for gid,t,o,z in rr:
        ob=mean(v for g,v in prod[t] if g!=gid); od=mean(v for g,v in deff[o] if g!=gid)
        db=mean(v for g,v in deff[t] if g!=gid); oo=mean(v for g,v in prod[o] if g!=gid)
        if ob is not None and od is not None:out.append(("offense",z,od,ob))
        if db is not None and oo is not None:out.append(("defense",-z,oo,db))
    return out
def rmse(cs,s):
    return math.sqrt(statistics.fmean((adjust(p,q,s)-base)**2 for _,p,q,base in cs)) if cs else None

train={y:rows(y) for y in TRAIN}; val={y:rows(y) for y in VALIDATE}
metrics={}
for m in METRICS:
    tr=sum((cases(train[y],m) for y in TRAIN),[])
    va=sum((cases(val[y],m) for y in VALIDATE),[])
    scores={str(s):rmse(va,s) for s in CANDIDATES}
    # Select on held-out 2025 only; ties favor the smaller intervention.
    best=min(CANDIDATES,key=lambda s:(scores[str(s)],s)) if va else 0.20
    metrics[m]={"selected_strength":best,"training_samples":len(tr),"validation_samples":len(va),
      "validation_rmse_raw":round(rmse(va,0.0),6) if va else None,
      "candidate_validation_rmse":{k:round(v,6) for k,v in scores.items() if v is not None}}
payload={"schema_version":"opponent-interaction-v13.0","training_seasons":list(TRAIN),"validation_seasons":list(VALIDATE),
 "candidate_strengths":list(CANDIDATES),"selection_rule":"lowest held-out 2025 RMSE per metric; ties favor smaller modifier",
 "interaction":"positive performance multiplied by difficulty modifier; negative performance divided by modifier; modifier=1+strength*signed_log(opponent_unit_sd), capped 0.55..1.45",
 "metrics":metrics}
OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(payload,indent=2)+"\n");print(json.dumps(payload,indent=2))
