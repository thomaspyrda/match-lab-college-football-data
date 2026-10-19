#!/usr/bin/env python3
"""Private sensitivity check: 15% uncapped margin, asymmetric SOS, -0.20 loss."""
import json,statistics
from collections import defaultdict
from pathlib import Path
root=Path(__file__).resolve().parent
exp=json.loads((root/"data/experiments/four_unit_chronological_10pct_margin_2026.json").read_text())
current=json.loads((root/"data/current_rankings.json").read_text())
history=json.loads((root/"data/historical/2026.json").read_text())["games"]
aliases={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
canon=lambda t:aliases.get(t,t)
teams={canon(r["team"]):r for r in exp["teams"]}
baseline={canon(r["team"]):r for r in current["teams"]}
assert len(teams)==136 and set(teams)==set(baseline)
through=exp["through_week"]
def mean(v):return statistics.fmean(v) if v else 0.
# Uncapped actual final game margins; opponent entering the week determined
# from completed previous games only; frozen once scored.
obs=defaultdict(list)
for g in history:
 result=g.get("result") or {}
 week=int(g.get("week") or 0)
 if not 1<=week<=through:continue
 h,a=canon(g["home"]),canon(g["away"])
 if h not in teams or a not in teams:continue
 try:hp=float(result["home_points"]);ap=float(result["away_points"])
 except (ValueError,TypeError,KeyError):continue
 obs[h].append((week,a,hp-ap))
 obs[a].append((week,h,ap-hp))
adj=defaultdict(list)
for week in range(1,through+1):
 prev={t:mean([m for w,o,m in obs[t] if w<week]) for t in teams if any(w<week for w,o,m in obs[t])}
 mu=mean(list(prev.values()))
 sd=statistics.pstdev(prev.values()) if len(prev)>1 else 14.
 for t in teams:
  for w,opp,margin in obs[t]:
   if w!=week:continue
   opponent_z=(prev[opp]-mu)/(sd or 14.) if opp in prev else 0.
   adj[t].append((week,margin/14.+.5*opponent_z))
def form(t):
 rows=sorted(adj[t]);ws=[1.]*len(rows)
 for back,w in ((1,2.),(2,1.5),(3,1.25)):
  if len(ws)>=back:ws[-back]=w
 return sum(row[1]*w for row,w in zip(rows,ws))/sum(ws)
form_values={t:form(t) for t in teams}
mu=mean(list(form_values.values()));sd=statistics.pstdev(form_values.values()) or 1.
sos=[float(r["schedule_strength"]) for r in baseline.values()]
sos_mu=mean(sos);sos_sd=statistics.pstdev(sos)
def score(t,uncapped):
 r=teams[t];b=baseline[t];z=(float(b["schedule_strength"])-sos_mu)/sos_sd
 sos_adj=.10*max(z,0)+.20*min(z,0)-.15*max(-z-1,0)
 four=(float(r["overall_z"])-.10*float(r["margin_z"])-float(r["ap_bonus"])+.10*int(r["losses"]))/.90
 margin_z=(form_values[t]-mu)/sd if uncapped else float(r["margin_z"])
 mix=.15 if uncapped else .10
 total=(1-mix)*four+mix*margin_z+float(r["ap_bonus"])-.20*int(r["losses"])+sos_adj
 return total,margin_z,sos_adj
old=sorted(teams,key=lambda t:(-score(t,False)[0],t))
new=sorted(teams,key=lambda t:(-score(t,True)[0],t))
oldpos={t:i for i,t in enumerate(old,1)}
newpos={t:i for i,t in enumerate(new,1)}
print("UNCAPPED_15_PERCENT_TEST|through_week",through,"|games",sum(len(v) for v in obs.values())//2,"|teams",len(teams))
print("RANK|TEAM|FINAL_Z|PREVIOUS_RANK|MOVE|UNCAPPED_MARGIN_Z|SOS_ADJUSTMENT|LOSSES")
for i,t in enumerate(new[:35],1):
 v,m,sa=score(t,True)
 print(f"{i}|{t}|{v:+.3f}|{oldpos[t]}|{oldpos[t]-i:+d}|{m:+.3f}|{sa:+.3f}|{teams[t]['losses']}")
for t in ("Liberty","Miami","BYU","Ole Miss","LSU","Kentucky","Mississippi State","Auburn","Texas Tech","James Madison","Georgia"):
 v,m,sa=score(t,True)
 print(f"TRACK|{t}|{oldpos[t]}|{newpos[t]}|{v:+.3f}|{m:+.3f}")
