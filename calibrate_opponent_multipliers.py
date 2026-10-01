#!/usr/bin/env python3
"""Calibrate continuous v9 opponent-quality sensitivity from historical FBS games."""
import json, os, statistics, urllib.parse, urllib.request
from collections import defaultdict
from pathlib import Path
from experiment_dominance_v8 import METRICS, canon, metric_row, f

ROOT=Path(__file__).resolve().parent
YEARS=(2022,2023,2024,2025)
OUT=ROOT/"data"/"experiments"/"opponent_multiplier_calibration_2022_2025.json"
KEY=os.environ.get("CFBD_API_KEY")
if not KEY: raise SystemExit("CFBD_API_KEY secret required")

def api(path,**params):
    url="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
    with urllib.request.urlopen(req,timeout=180) as r:return json.load(r)

def median(xs):
    xs=[x for x in xs if x is not None]
    return statistics.median(xs) if xs else None

samples=defaultdict(lambda:{"offense":[],"defense":[]})
year_counts={}
for year in YEARS:
    games=api("/games",year=year,seasonType="regular")
    adv=api("/stats/game/advanced",year=year,seasonType="regular",excludeGarbageTime="true")
    by_gid=defaultdict(dict)
    for row in adv:
        if row.get("team"): by_gid[str(row.get("gameId"))][canon(row["team"])]=row
    fbs={canon(x["school"]) for x in api("/teams/fbs",year=year) if x.get("school")}
    observations=[]
    for g in games:
        if not g.get("completed", True): continue
        gid=str(g.get("id")); h=canon(g.get("homeTeam")); a=canon(g.get("awayTeam")); rows=by_gid.get(gid,{})
        if h not in fbs or a not in fbs or h not in rows or a not in rows: continue
        observations.extend([(gid,h,a,metric_row(rows[h],g.get("homePoints"))),(gid,a,h,metric_row(rows[a],g.get("awayPoints")))])
    year_counts[str(year)]={"fbs_team_game_rows":len(observations)}
    for m in METRICS:
        vals=[r[3][m] for r in observations if r[3][m] is not None]
        if len(vals)<20: continue
        mu=statistics.fmean(vals); sd=statistics.pstdev(vals) or 1.0
        zrows=[(gid,t,o,(mr[m]-mu)/sd) for gid,t,o,mr in observations if mr[m] is not None]
        produced=defaultdict(list); allowed=defaultdict(list)
        for gid,t,o,z in zrows:
            produced[t].append((gid,z)); allowed[o].append((gid,-z))
        for gid,t,o,z in zrows:
            oq=[v for g2,v in produced[o] if g2!=gid]; dq=[v for g2,v in allowed[o] if g2!=gid]
            if oq: samples[m]["defense"].append((statistics.fmean(oq),-z))
            if dq: samples[m]["offense"].append((statistics.fmean(dq),z))
metrics={}
for m in METRICS:
    metrics[m]={}
    for side in ("offense","defense"):
        ps=samples[m][side]
        metrics[m][side]={"sensitivity":round(fit(ps),6),"samples":len(ps)}
payload={"schema_version":"opponent-multiplier-1.0","training_seasons":list(YEARS),
 "method":"leave-one-game-out historical FBS opponent-unit quality; continuous exponential multiplier; no tiers",
 "year_counts":year_counts,"metrics":metrics}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2)+"\\n")
print(json.dumps(payload,indent=2))
