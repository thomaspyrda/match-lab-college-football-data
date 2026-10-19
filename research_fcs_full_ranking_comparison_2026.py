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

# FCS special-performance penalties; standardized loss penalty is already in score().
penalties=defaultdict(float);cases=[]
for g in history:
 week=int(g.get("week") or 0);result=g.get("result") or {}
 if not 1<=week<=through:continue
 h,a=canon(g.get("home","")),canon(g.get("away",""))
 if (h in teams)==(a in teams):continue
 try:hp=float(result["home_points"]);ap=float(result["away_points"])
 except (ValueError,TypeError,KeyError):continue
 t=h if h in teams else a;opp=a if h in teams else h
 margin=(hp-ap) if t==h else (ap-hp)
 pen=.10 if 7<=margin<=10 else .20 if 1<=margin<=6 else .35 if -10<=margin<=-1 else .45 if margin<=-11 else 0
 if pen:
  penalties[t]+=pen;cases.append((t,opp,week,margin,pen,hp,ap))
base_rank=sorted(teams,key=lambda t:(-score(t,True)[0],t))
new_rank=sorted(teams,key=lambda t:(-(score(t,True)[0]-penalties[t]),t))
basepos={t:i for i,t in enumerate(base_rank,1)}
newpos={t:i for i,t in enumerate(new_rank,1)}
print("FCS_FULL_COMPARE|through",through,"|affected_teams",len(penalties),"|qualifying_games",len(cases))
print("RANK|TEAM|NEW_SCORE|BASE_RANK|MOVE|FCS_PENALTY")
for i,t in enumerate(new_rank[:35],1):
 print(f"{i}|{t}|{score(t,True)[0]-penalties[t]:+.3f}|{basepos[t]}|{basepos[t]-i:+d}|{-penalties[t]:+.2f}")
print("ALL_QUALIFYING_TEAMS")
for t in sorted(penalties):
 print(f"TEAM|{t}|BASE_RANK={basepos[t]}|NEW_RANK={newpos[t]}|PENALTY={-penalties[t]:+.2f}")
for t,opp,week,margin,pen,hp,ap in cases:
 print(f"CASE|{t}|{opp}|week={week}|FBS_MARGIN={margin:+.0f}|PENALTY=-{pen:.2f}|home={hp:.0f}|away={ap:.0f}")
