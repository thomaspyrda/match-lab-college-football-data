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
    fbs_values=defaultdict(list); fcs_games=[]
    for g in games:
        if not g.get("completed", True): continue
        gid=str(g.get("id")); h=canon(g.get("homeTeam")); a=canon(g.get("awayTeam"))
        rows=by_gid.get(gid,{})
        if h not in rows or a not in rows: continue
        hp=g.get("homePoints"); ap=g.get("awayPoints")
        hm=metric_row(rows[h],hp); am=metric_row(rows[a],ap)
        hf=h in fbs; af=a in fbs
        if hf and af:
            for row in (hm,am):
                for m in METRICS:
                    if row[m] is not None:fbs_values[m].append(row[m])
        elif hf != af:
            t,own,opp=(h,hm,am) if hf else (a,am,hm)
            fcs_games.append((t,own,opp))
    mus={m:statistics.fmean(fbs_values[m]) for m in METRICS if fbs_values[m]}
    sds={m:(statistics.pstdev(fbs_values[m]) or 1.0) for m in METRICS if fbs_values[m]}
    used=0
    for t,own,opp in fcs_games:
        any_used=False
        for m in METRICS:
            if m not in mus: continue
            if own[m] is not None:
                samples[m]["offense"].append((own[m]-mus[m])/sds[m]); any_used=True
            if opp[m] is not None:
                samples[m]["defense"].append(-((opp[m]-mus[m])/sds[m])); any_used=True
        used+=int(any_used)
    year_counts[str(year)]={"fbs_fcs_games_with_advanced_data":used,"candidate_games":len(fcs_games)}

metrics={}
for m in METRICS:
    off=samples[m]["offense"]; de=samples[m]["defense"]
    metrics[m]={"offense_expected_z":round(median(off),4) if off else None,
                "defense_expected_z":round(median(de),4) if de else None,
                "offense_samples":len(off),"defense_samples":len(de)}
payload={"schema_version":"fcs-calibration-2.0","training_seasons":list(YEARS),
 "statistic":"median historical FBS performance vs FCS, standardized within each season against FBS-vs-FBS game distributions",
 "positive_effect_cap":0.0,"year_counts":year_counts,"metrics":metrics}
OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(payload,indent=2)+"\n")
print(json.dumps(payload,indent=2))
