#!/usr/bin/env python3
"""PRIVATE research only; prints rankings; never writes production files."""
import json,os,urllib.request,urllib.parse,statistics
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parent
KEY=os.environ["CFBD_API_KEY"]
def api(path,**kw):
  u="https://api.collegefootballdata.com"+path+"?"+urllib.parse.urlencode(kw)
  req=urllib.request.Request(u,headers={"Authorization":"Bearer "+KEY,"Accept":"application/json","User-Agent":"MatchLab/1.0"})
  with urllib.request.urlopen(req,timeout=150) as x:return json.load(x)
def name(t):return {"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}.get(t,t)
def val(x):
  try:return float(x) if x is not None else None
  except:return None
def avg(a):return statistics.fmean(a) if a else None
hist=json.loads((ROOT/"data/historical/2026.json").read_text())["games"]
past=json.loads((ROOT/"data/frozen_conference_rankings_2026_week6.json").read_text())["rows"]
fbs={name(x["team"]) for x in past}; prior={name(x["team"]):x for x in past}
games={str(g["game_id"]):g for g in hist if g.get("result") and 1<=int(g.get("week") or 0)<=7}
adv=api("/stats/game/advanced",year=2026,seasonType="regular",excludeGarbageTime="true")
bygid=defaultdict(dict)
for x in adv:
  if x.get("team"):bygid[str(x.get("gameId"))][name(x["team"])]=x
# PO/R: 45% PPA, 45% success, 10% explosiveness.
# RO/R: 40% PPA, 40% success, 20% explosiveness.
# Game observations: offense positive; defense negative of opponent offense.
metrics=["ppa","successRate","explosiveness"]
weights={"p":[.45,.45,.10],"r":[.40,.40,.20]}
rows=[]; nskipped=0
for gid,g in games.items():
  h,a=name(g["home"]),name(g["away"])
  if h not in fbs or a not in fbs:continue
  if h not in bygid[gid] or a not in bygid[gid]:nskipped+=1;continue
  week=int(g["week"])
  for team,opp in ((h,a),(a,h)):
    own=bygid[gid][team].get("offense") or {}
    other=bygid[gid][opp].get("offense") or {}
    for unit,path in (("PO","passingPlays"),("RO","rushingPlays"),("PD","passingPlays"),("RD","rushingPlays")):
      raw=own if unit.endswith("O") else other
      stat=raw.get(path) or {}
      values=[val(stat.get(m)) for m in metrics]
      if any(v is None for v in values):continue
      rows.append((team,opp,week,unit,values, -1 if unit.endswith("D") else 1))
assert len(rows)>700,(len(rows),nskipped)
# Normalize metrics over observed games; one normalization, no recursion.
norm={}
for side in "pr":
 for j in range(3):
  v=[row[4][j] for row in rows if (row[3][0] in ("P" if side=="p" else "R"))]
  norm[side,j]=(avg(v),statistics.pstdev(v) or 1)
unadjusted=defaultdict(list)
for team,opp,week,unit,values,sign in rows:
 side=unit[0].lower()
 result=sum(w*sign*(v-norm[side,j][0])/norm[side,j][1] for j,(w,v) in enumerate(zip(weights[side],values)))
 unadjusted[(team,unit)].append((week,opp,result))
# Use last week's already-opponent-adjusted four-unit ratings as FIXED opponent benchmarks.
# They are NOT recomputed, so this is non-recursive.
unit_key={"PO":"passing_offense","RO":"rushing_offense","PD":"passing_defense","RD":"rushing_defense"}
peer_unit={"PO":"PD","RO":"RD","PD":"PO","RD":"RO"}
peer_ratings={u:[val(p[unit_key[u]]) for p in past] for u in unit_key}
peer_sd={u:(avg(v),statistics.pstdev(v) or 1) for u,v in peer_ratings.items()}
scores={}
for team in fbs:
 for unit in unit_key:
  obs=unadjusted.get((team,unit),[])
  if not obs:continue
  adjusted=[]
  for week,opp,raw in obs:
   if week==7 and opp in prior:
    peer=peer_unit[unit]; x=val(prior[opp][unit_key[peer]])
    z=((x-peer_sd[peer][0])/peer_sd[peer][1]) if x is not None else 0
    raw+=.35*z
   adjusted.append(raw)
  scores[(team,unit)]=avg(adjusted)
def rating(t,u):
 x=scores.get((t,u))
 if x is None:return None
 return x
overall=[]
for t in fbs:
 v=[rating(t,u) for u in ("PO","RO","PD","RD")]
 if any(x is None for x in v):continue
 overall.append((t,avg(v),*v))
overall.sort(key=lambda x:x[1],reverse=True)
print("MODEL: Nonrecursive. Weeks 1-6 raw game-level four-unit z metrics; Week 7 one-time opponent adjustment using frozen through-Week-6 opponent PO/RO/PD/RD ratings. Pass weights 45/45/10; rush 40/40/20. Equal four-unit Team Strength.")
print("COVERAGE",len(games),"completed games,",len(rows),"unit observations;",nskipped,"games skipped for missing advanced data;",len(overall),"teams with all units.")
print("RANK|TEAM|COMPOSITE_Z|PO_Z|RO_Z|PD_Z|RD_Z")
for i,(t,score,po,ro,pd,rd) in enumerate(overall[:25],1):
 print(f"{i}|{t}|{score:+.3f}|{po:+.3f}|{ro:+.3f}|{pd:+.3f}|{rd:+.3f}")
