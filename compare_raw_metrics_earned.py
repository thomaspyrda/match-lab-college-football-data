#!/usr/bin/env python3
"""Controlled research comparison: credit strong pregame opponents only for earned results."""
import csv,json,statistics,math
from collections import defaultdict
from pathlib import Path
D=Path(__file__).resolve().parent/"data"/"research"/"2026"
models=json.loads((D/"ranking_experiments.json").read_text())["variants"]
base=models["raw_metrics_balanced"]
strength={x["team"]:x for x in base}
pregame=list(csv.DictReader((D/"pregame_opponent_exposure.csv").open()))
raw=list(csv.DictReader((D/"weekly_team_metrics.csv").open()))
aliases={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def canon(s):return aliases.get(s,s)
results={(g["game_id"],canon(g["team"])):g for g in raw}
exposure=defaultdict(list)
detail=[]
for p in pregame:
    t=canon(p["team"]);key=(p["game_id"],t)
    game=results.get(key)
    if t not in strength or not game:continue
    tp=float(game["team_points"]);op=float(game["opponent_points"])
    s=float(p["pregame_opponent_strength"]);ts=float(p["pregame_team_strength"])
    # Win is required for full reward. A competitive loss is not a quality win,
    # but can earn modest credit from exceeding a pregame expectation.
    expected=7*(ts-s)
    relative=max(-1.,min(1.,((tp-op)-expected)/35.))
    win=tp>op
    earned=1. if win else .25*max(0.,relative)
    contribution=max(-2.,min(2.,s))*earned
    exposure[t].append(contribution)
    detail.append({"team":t,"week":p["week"],"opponent":canon(p["opponent"]),
      "pregame_opponent_strength":round(s,4),"won":int(win),
      "performance_residual":round(relative,4),"earned_exposure":round(contribution,4)})
def z(v):
    mu=statistics.fmean(v.values())
    sd=statistics.pstdev(v.values()) or 1.
    return {k:(x-mu)/sd for k,x in v.items()}
earned={t:statistics.fmean(exposure[t]) if exposure[t] else 0. for t in strength}
# Base composite is already normalized 60/25/15; test a bounded 10% earned
# exposure overlay rather than an unconditional SOS/conf bonus.
base_z=z({t:float(x["score"]) for t,x in strength.items()})
earned_z=z(earned)
comparison=sorted([{"team":t,"score":round(.90*base_z[t]+.10*earned_z[t],5),
 "earned_exposure_z":round(earned_z[t],5),"baseline_rank":int(strength[t]["rank"]),
 "baseline_score":strength[t]["score"],"fbs_games":strength[t]["games"]}
 for t in strength],key=lambda r:(-r["score"],r["team"]))
for i,r in enumerate(comparison,1):r["rank"]=i;r["change"]=r["baseline_rank"]-i
with (D/"raw_metrics_earned_exposure_comparison.csv").open("w",newline="") as f:
    fields=list(comparison[0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(comparison)
with (D/"raw_metrics_earned_exposure_game_audit.csv").open("w",newline="") as f:
    fields=list(detail[0]);w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(detail)
(D/"raw_metrics_earned_exposure_summary.json").write_text(json.dumps({"method":"90% raw-metrics balanced model + 10% earned pregame opponent exposure",
 "caveat":"Experimental; frozen opponent strengths retain preseason anchoring; confidence may overlap existing result credits.",
 "top25":comparison[:25],"watch":[r for r in comparison if r["team"] in
 ["Georgia","Miami","Notre Dame","Ohio State","BYU","Alabama","Indiana","Utah","Kentucky","Texas","Florida","Oregon"]]},indent=2))
print("Top 25:",[(r["rank"],r["team"]) for r in comparison[:25]])
