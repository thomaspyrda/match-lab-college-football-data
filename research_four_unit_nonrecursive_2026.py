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
# For each game week, derive opponent benchmarks using only earlier weeks.
# Ratings are raw (not recursively adjusted); 0.50 * opponent-unit Z for every week.
peer_unit={"PO":"PD","RO":"RD","PD":"PO","RD":"RO"}
fixed_week_benchmarks={}
for week in range(1,8):
 fixed_week_benchmarks[week]={}
 for unit in ("PO","RO","PD","RD"):
  prior_vals={t:avg([raw for wk,opp,raw in unadjusted.get((t,unit),[]) if wk<week]) for t in fbs}
  populated=[v for v in prior_vals.values() if v is not None]
  mu=avg(populated) if populated else 0.0
  sd=statistics.pstdev(populated) if len(populated)>1 else 1.0
  fixed_week_benchmarks[week][unit]={t:((v-mu)/(sd or 1)) for t,v in prior_vals.items() if v is not None}
# AP pregame rankings from historical weekly polling. Quality win z bonus is capped.
polls=api("/rankings",year=2026,seasonType="regular")
ap_by_week={}
for item in polls:
 wk=int(item.get("week") or 0)
 poll=next((p for p in item.get("polls",[]) if str(p.get("poll","")).lower() in ("ap top 25","ap")),None)
 if poll:
  ap_by_week[wk]={name(t.get("school") or t.get("team") or ""):int(t.get("rank") or 999) for t in poll.get("ranks",[])}
def ap_pregame(wk,team):
 # Pregame poll: prefer same-week published AP ranking; avoid later polls.
 ranks=ap_by_week.get(wk) or ap_by_week.get(wk-1) or {}
 return ranks.get(team)
# A win over AP #1–5 adds .25 z, #6–10 .20, #11–15 .15, #16–20 .10, #21–25 .05.
win_bonus=defaultdict(float)
ranked_wins=defaultdict(list)
for g in games.values():
 res=g.get("result") or {}
 hp,ap=val(res.get("home_points")),val(res.get("away_points"))
 if hp is None or ap is None or hp==ap:continue
 winner=name(g["home"] if hp>ap else g["away"]);loser=name(g["away"] if hp>ap else g["home"])
 if winner not in fbs:continue
 rank=ap_pregame(int(g["week"]),loser)
 if rank is None or rank>25:continue
 bonus=.25 if rank<=5 else .20 if rank<=10 else .15 if rank<=15 else .10 if rank<=20 else .05
 win_bonus[winner]+=bonus
 ranked_wins[winner].append((loser,rank,bonus))
# Preserve per-game evidence for alternative recency weighting.
adjusted_obs=defaultdict(list)
for team in fbs:
 for unit in ("PO","RO","PD","RD"):
  for week,opp,raw in unadjusted.get((team,unit),[]):
   opponent_z=fixed_week_benchmarks[week][peer_unit[unit]].get(opp,0.0)
   adjusted_obs[(team,unit)].append((week,raw+0.50*opponent_z))
def unit_for(t,u,mult):
 obs=adjusted_obs.get((t,u),[])
 if not obs:return None
 latest=max(w for w,v in obs)
 numerator=sum(v*(mult if w==latest else 1) for w,v in obs)
 denom=sum(mult if w==latest else 1 for w,v in obs)
 return numerator/denom
def meanunits(t,mult):
 vals=[unit_for(t,u,mult) for u in ("PO","RO","PD","RD")]
 return avg(vals) if all(x is not None for x in vals) else None
def model_702010(t):
 season=meanunits(t,1.0)
 # Latest week: use four-unit performance from the team's latest completed game week.
 latest=max((wk for u in ("PO","RO","PD","RD") for wk,v in adjusted_obs.get((t,u),[])),default=0)
 recent=avg([v for u in ("PO","RO","PD","RD") for wk,v in adjusted_obs.get((t,u),[]) if wk==latest])
 if season is None or recent is None:return None
 # A 10% quality-win component: normalized cumulative ranked-win bonus, capped at 0.5 z.
 return .70*season+.20*recent+.10*min(win_bonus[t]/.50,1.0)
def model_weight(t,mult):
 return meanunits(t,mult)
print("COVERAGE",len(games),"games",len(rows),"four-unit observations",nskipped,"missing advanced games",len(fbs),"FBS teams")
print("BONUS COUNTS",sum(bool(x) for x in ranked_wins.values()),"teams",sum(len(x) for x in ranked_wins.values()),"AP ranked wins; example",ranked_wins.get("BYU"))
for label,fn in (("70/20/10",model_702010),("Latest 1.5x",lambda t:model_weight(t,1.5)),("Latest 2x",lambda t:model_weight(t,2))):
 ranking=sorted(((t,fn(t)) for t in fbs if fn(t) is not None),key=lambda x:x[1],reverse=True)
 print("MODEL",label,"TEAMS",len(ranking))
 print("RANK|TEAM|SCORE|RANKED_WINS")
 for i,(t,v) in enumerate(ranking[:25],1):
  print(f"{i}|{t}|{v:+.3f}|{','.join(opp+'#'+str(rank) for opp,rank,b in ranked_wins[t]) or '-'}")
