#!/usr/bin/env python3
"""Private, read-only strong SOS adjustment comparison; no production writes."""
import json,statistics
from pathlib import Path
root=Path(__file__).resolve().parent
exp=json.loads((root/"data/experiments/four_unit_chronological_10pct_margin_2026.json").read_text())
cur=json.loads((root/"data/current_rankings.json").read_text())
aliases={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
canon=lambda n:aliases.get(n,n)
data={canon(r["team"]):r for r in cur["teams"]}
rows=exp["teams"]; assert len(rows)==136
valid=[(r,data[canon(r["team"])]) for r in rows]
assert len(valid)==136 and all(a.get("schedule_strength") is not None for r,a in valid)
sos=[float(a["schedule_strength"]) for r,a in valid]
mu=statistics.fmean(sos); sd=statistics.pstdev(sos)
assert sd>0
original=sorted(valid,key=lambda pair:(-float(pair[0]["overall_z"]),pair[0]["team"]))
old_pos={canon(r["team"]):i for i,(r,a) in enumerate(original,1)}
# Asymmetric: 0.10 positive credit, 0.20 negative Z, plus 0.15 extra
# for schedules more than 1 SD weaker than FBS average.
print("LOSS_PENALTY_COMPARE|ASYMMETRIC_SOS|136 FBS|current -0.10 vs -0.20 vs -0.25")
all_results={}
for loss_rate in (0.10,0.20,0.25):
 adjusted=[]
 for r,a in valid:
  team=canon(r["team"]);z=(float(a["schedule_strength"])-mu)/sd
  sos_adj=.10*max(z,0)+.20*min(z,0)-.15*max(-z-1,0)
  losses=int(r["losses"])
  score=float(r["overall_z"])+sos_adj-(loss_rate-.10)*losses
  adjusted.append({"team":team,"score":score,"losses":losses,"sos_adj":sos_adj})
 adjusted.sort(key=lambda x:(-x["score"],x["team"]))
 all_results[loss_rate]={x["team"]:(i,x["score"]) for i,x in enumerate(adjusted,1)}
 print(f"MODEL|loss=-{loss_rate:.2f}")
 print("RANK|TEAM|SCORE|LOSSES|SOS_ADJ")
 for i,x in enumerate(adjusted[:25],1):print(f"{i}|{x['team']}|{x['score']:+.3f}|{x['losses']}|{x['sos_adj']:+.3f}")
for team in ("LSU","Kentucky","Mississippi State","Auburn","Miami","BYU","Ole Miss","Liberty","Texas","Georgia","Ohio State","James Madison","Florida","Oklahoma"):
 print("TRACK|"+team+"|"+ "|".join(f"-{penalty:.2f}:#{all_results[penalty][team][0]}:{all_results[penalty][team][1]:+.3f}" for penalty in (0.10,0.20,0.25)))
