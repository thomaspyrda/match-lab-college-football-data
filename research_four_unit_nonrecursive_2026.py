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
# Chronological nonrecursive evidence: an opponent's pregame strength comes
# ONLY from adjusted games completed in prior weeks. Freeze each game on entry.
peer_unit={"PO":"PD","RO":"RD","PD":"PO","RD":"RO"}
adjusted_obs=defaultdict(list)
coverage_by_week={}
for week in range(1,8):
 fixed={}
 for unit in ("PO","RO","PD","RD"):
  values={t:avg([score for wk,score in adjusted_obs.get((t,unit),[])]) for t in fbs}
  present=[x for x in values.values() if x is not None]
  center=avg(present) if present else 0.0
  sd=statistics.pstdev(present) if len(present)>1 else 1.0
  fixed[unit]={t:(v-center)/(sd or 1.0) for t,v in values.items() if v is not None}
 coverage_by_week[week]={unit:len(vals) for unit,vals in fixed.items()}
 additions=defaultdict(list)
 for (team,unit),observations in unadjusted.items():
  for wk,opp,raw in observations:
   if wk!=week:continue
   opponent_z=fixed[peer_unit[unit]].get(opp,0.0)
   additions[(team,unit)].append((week,raw+0.50*opponent_z))
 for key,vals in additions.items():adjusted_obs[key].extend(vals)
print("PREGAME COVERAGE",coverage_by_week)
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
# Overall-only adjustments; individual four-unit values remain untouched.
losses=defaultdict(int)
for g in games.values():
 res=g.get("result") or {}
 hp,ap=val(res.get("home_points")),val(res.get("away_points"))
 if hp is None or ap is None or hp==ap:continue
 loser=name(g["away"] if hp>ap else g["home"])
 if loser in fbs:losses[loser]+=1
def model_winloss(t):
 base=meanunits(t,2.0)
 return None if base is None else base+win_bonus[t]-.10*losses[t]
ranking=sorted(((t,model_winloss(t)) for t in fbs if model_winloss(t) is not None),key=lambda x:x[1],reverse=True)
print("MODEL CHRONOLOGICAL FROZEN pregame opponent-adjusted units, 2x latest game + AP ranked wins + 0.10 loss penalty")
print("RANK|TEAM|OVERALL_Z|BASE_Z|WIN_BONUS|LOSSES|LOSS_PENALTY")
for i,(t,v) in enumerate(ranking[:25],1):
 print(f"{i}|{t}|{v:+.3f}|{meanunits(t,2.0):+.3f}|{win_bonus[t]:+.3f}|{losses[t]}|{-0.10*losses[t]:+.3f}")
# Compare latest-game 2x baseline to last-three form (1.25x,1.50x,2x).
def three_game_unit(t,u):
 obs=adjusted_obs.get((t,u),[])
 if not obs:return None
 # Chronological completed games, not calendar weeks, so bye weeks do not count.
 chronological=sorted(obs,key=lambda x:x[0])
 weights=[1.0]*len(chronological)
 for back,w in ((1,2.0),(2,1.50),(3,1.25)):
  if len(weights)>=back:weights[-back]=w
 return sum(v*w for (_,v),w in zip(chronological,weights))/sum(weights)
def three_game_base(t):
 vals=[three_game_unit(t,u) for u in ("PO","RO","PD","RD")]
 return avg(vals) if all(v is not None for v in vals) else None
def three_game_total(t):
 base=three_game_base(t)
 return None if base is None else base+win_bonus[t]-.10*losses[t]
base_rank=sorted(((t,model_winloss(t)) for t in fbs if model_winloss(t) is not None),key=lambda x:x[1],reverse=True)
prior_pos={t:i for i,(t,_) in enumerate(base_rank,1)}
new_rank=sorted(((t,three_game_total(t)) for t in fbs if three_game_total(t) is not None),key=lambda x:x[1],reverse=True)
print("MODEL COMPARE: last game 2x versus last three played 1.25x/1.50x/2x, same frozen chronological opponent adjustment and quality wins/losses")
print("NEW_RANK|TEAM|NEW_TOTAL|PREVIOUS_RANK|DELTA|THREE_GAME_BASE|AP_BONUS|LOSS_COUNT")
for i,(t,v) in enumerate(new_rank[:35],1):
 print(f"{i}|{t}|{v:+.3f}|{prior_pos[t]}|{prior_pos[t]-i:+d}|{three_game_base(t):+.3f}|{win_bonus[t]:+.3f}|{losses[t]}")
print("CHECKS BYU LSU Mississippi State Oregon Georgia Ohio State")
for t in ("BYU","LSU","Mississippi State","Oregon","Georgia","Ohio State"):
 row=next((j for j,(x,_) in enumerate(new_rank,1) if x==t),None)
 print(f"CHECK|{t}|new={row}|old={prior_pos.get(t)}|oldscore={model_winloss(t)}|newscore={three_game_total(t)}")
# Opponent-adjusted capped scoring margin. Each game's benchmark is frozen
# using ONLY scoring margins of opponents prior to the game week.
margin_by_team=defaultdict(list)
for g in games.values():
 res=g.get("result") or {};hp,ap=val(res.get("home_points")),val(res.get("away_points"))
 if hp is None or ap is None:continue
 h,a=name(g["home"]),name(g["away"]);wk=int(g["week"])
 if h in fbs and a in fbs:
  margin_by_team[h].append((wk,a,max(-28,min(28,hp-ap))))
  margin_by_team[a].append((wk,h,max(-28,min(28,ap-hp))))
# Game margin / typical 14-point range scaled into approximate z score.
# Adj = own capped margin z + .5 * opposing pregame margin strength z.
adjusted_margin=defaultdict(list)
for wk in range(1,8):
 strength={t:avg([m for w,o,m in margin_by_team[t] if w<wk]) for t in fbs}
 known=[v for v in strength.values() if v is not None]
 mu=avg(known) if known else 0.0
 sd=statistics.pstdev(known) if len(known)>1 else 14.0
 for team,observations in margin_by_team.items():
  for week,opp,margin in observations:
   if week!=wk:continue
   opponent_pregame=(strength[opp]-mu)/(sd or 14) if strength.get(opp) is not None else 0.0
   adjusted_margin[team].append((week,margin/14.0+0.5*opponent_pregame))
def weighted_form(obs):
 obs=sorted(obs,key=lambda x:x[0])
 if not obs:return None
 ws=[1.0]*len(obs)
 for back,w in ((1,2.0),(2,1.5),(3,1.25)):
  if len(ws)>=back:ws[-back]=w
 return sum(v*w for (_,v),w in zip(obs,ws))/sum(ws)
# Normalize margin form against all FBS for comparable scaling.
margins={t:weighted_form(adjusted_margin[t]) for t in fbs}
values=[v for v in margins.values() if v is not None]
mu=avg(values);sd=statistics.pstdev(values) or 1
margin_z={t:(v-mu)/sd for t,v in margins.items() if v is not None}
def margin_model(t,mix):
 four=three_game_base(t)
 if four is None or t not in margin_z:return None
 return (1-mix)*four+mix*margin_z[t]+win_bonus[t]-.1*losses[t]
base_positions={t:i for i,(t,score) in enumerate(new_rank,1)}
print("MARGIN_TEST margin capped +-28, each week's frozen pregame opponent strength, three-game form, 10/20 pct blend")
for mix in (0.1,0.2):
 result=sorted(((t,margin_model(t,mix)) for t in fbs if margin_model(t,mix) is not None),key=lambda x:x[1],reverse=True)
 positions={t:i for i,(t,score) in enumerate(result,1)}
 print("MARGIN_MODEL",int(mix*100),"TEAMS",len(result))
 print("RANK|TEAM|SCORE|BASE_RANK|RANK_CHANGE|MARGIN_Z")
 for i,(t,v) in enumerate(result[:30],1):
  print(f"{i}|{t}|{v:+.3f}|{base_positions[t]}|{base_positions[t]-i:+d}|{margin_z[t]:+.3f}")
 for t in ("Miami","BYU","Ole Miss","LSU","Kentucky","Mississippi State","Wake Forest","Florida State"):
  if t in positions:print(f"MARGIN_CHECK|{int(mix*100)}|{t}|{base_positions[t]}|{positions[t]}|{margin_z[t]:+.3f}")
print("COVERAGE",len(games),"games",len(rows),"four-unit observations",nskipped,"missing advanced games",len(fbs),"FBS teams")
print("BONUS COUNTS",sum(bool(x) for x in ranked_wins.values()),"teams",sum(len(x) for x in ranked_wins.values()),"AP ranked wins; example",ranked_wins.get("BYU"))
for label,fn in (("70/20/10",model_702010),("Latest 1.5x",lambda t:model_weight(t,1.5)),("Latest 2x",lambda t:model_weight(t,2))):
 ranking=sorted(((t,fn(t)) for t in fbs if fn(t) is not None),key=lambda x:x[1],reverse=True)
 print("MODEL",label,"TEAMS",len(ranking))
 print("RANK|TEAM|SCORE|RANKED_WINS")
 for i,(t,v) in enumerate(ranking[:25],1):
  print(f"{i}|{t}|{v:+.3f}|{','.join(opp+'#'+str(rank) for opp,rank,b in ranked_wins[t]) or '-'}")
