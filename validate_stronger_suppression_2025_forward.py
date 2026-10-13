#!/usr/bin/env python3
"""Historical prospective 2025 comparison: unchanged unit control vs mild/strong.
Week W-1 unit snapshots evaluate Week W FBS-vs-FBS games. Unit forecasts evaluated
using pregame-normalized raw game unit measurements, win discrimination and margin.
This DOES NOT claim full 25/35/25/15 validation, since historical pregame
market/ATS/competition components are not fully reconstructed.
"""
import csv,json,statistics,math
from pathlib import Path
from collections import defaultdict
P=Path("data/research/2025"); UNITS=("PO","PD","RO","RD")
SPEC={"PO":[("passing_ppa",.4),("passing_success",.4),("passing_20plus_rate",.2)],
"PD":[("passing_ppa",.4),("passing_success",.4),("passing_20plus_rate",.2)],
"RO":[("rushing_success",.25),("rushing_ppa",.2),("stuff_avoidance",.17),("line_yards",.14),("power_success",.11),("second_level_yards",.08),("open_field_yards",.05)],
"RD":[("rushing_success",.25),("rushing_ppa",.2),("stuff_avoidance",.17),("line_yards",.14),("power_success",.11),("second_level_yards",.08),("open_field_yards",.05)]}
def read(path):return list(csv.DictReader((P/path).open()))
mild=read("opponent_unit_custom_suppression_weekly_comparison.csv")
strong=read("opponent_unit_stronger_suppression_weekly_comparison.csv")
allrows={"control":mild,"mild_1_5_to_35":mild,"strong_3_to_45":strong}
rankings={}
for model,rows in allrows.items():
 amp=0 if model=="control" else 1
 rankings[model]={(int(r["through_week"]),r["team"],r["unit"]):float(r["z"]) for r in rows if float(r["max_suppression"])==amp}
games=read("weekly_team_metrics.csv")
teams={r["team"] for r in mild}
games=[g for g in games if g["fbs_opponent"]=="1" and g["team"] in teams and g["opponent"] in teams]
schedule=read("games.csv")
by_game={(str(x["week"]),str(x["game_id"]),x["team"]):x for x in games}
def numeric(v):
 try:
  x=float(v);return x if math.isfinite(x) else None
 except (TypeError,ValueError):return None
def pearson(pairs):
 if len(pairs)<5:return None
 x=[a for a,b in pairs];y=[b for a,b in pairs]
 mx=statistics.fmean(x);my=statistics.fmean(y)
 den=(sum((v-mx)**2 for v in x)*sum((v-my)**2 for v in y))**.5
 return sum((v-mx)*(w-my) for v,w in pairs)/den if den else None
def auc(pairs):
 # fraction of predicted-strength ordering correctly separates winners and losers.
 pos=[x for x,y in pairs if y==1];neg=[x for x,y in pairs if y==0]
 if not pos or not neg:return None
 # rank sum with exact ties, O(nlogn)
 items=sorted([(x,1) for x in pos]+[(x,0) for x in neg])
 n=0;wins=0.;i=0
 while i<len(items):
  j=i+1
  while j<len(items) and items[j][0]==items[i][0]:j+=1
  p=sum(label for _,label in items[i:j]);z=(j-i)-p
  wins+=p*n+0.5*p*z;n+=z;i=j
 return wins/(len(pos)*len(neg))
def round_or_none(v):return round(v,6) if v is not None else None
metrics=defaultdict(lambda:defaultdict(list))
for wk in sorted({int(g["week"]) for g in games}):
 if wk<3:continue
 prev=[g for g in games if int(g["week"])<wk]
 scales={}
 for side in ("off","def"):
  for stat in set(q for spec in SPEC.values() for q,_ in spec):
   vals=[numeric(g.get(f"{side}_{stat}")) for g in prev]
   vals=[x for x in vals if x is not None]
   if len(vals)>=30:scales[side,stat]=(statistics.fmean(vals),statistics.pstdev(vals) or 1.)
 def actual_unit(game,unit):
  side="off" if unit in ("PO","RO") else "def"; z=[]
  for stat,weight in SPEC[unit]:
   value=numeric(game.get(f"{side}_{stat}"))
   if value is None or (side,stat) not in scales:continue
   mu,sd=scales[side,stat];z.append(((value-mu)/sd*(-1 if side=="def" else 1),weight))
  return sum(x*w for x,w in z)/sum(w for _,w in z) if z else None
 for g in games:
  if int(g["week"])!=wk:continue
  t=g["team"]
  scores={u:actual_unit(g,u) for u in UNITS}
  if any(x is None for x in scores.values()):continue
  for model,rs in rankings.items():
   if any((wk-1,t,u) not in rs for u in UNITS):continue
   for u in UNITS:metrics[model][u].append((rs[wk-1,t,u],scores[u]))
 for match in schedule:
  if int(match["week"])!=wk:continue
  h,a=match["home"],match["away"]
  if h not in teams or a not in teams:continue
  home_row=by_game.get((str(wk),str(match["game_id"]),h));away_row=by_game.get((str(wk),str(match["game_id"]),a))
  if home_row is None or away_row is None:continue
  margin=float(match["home_points"])-float(match["away_points"])
  for model,rs in rankings.items():
   if any((wk-1,t,u) not in rs for t in (h,a) for u in UNITS):continue
   h_strength=statistics.fmean(rs[wk-1,h,u] for u in UNITS)
   a_strength=statistics.fmean(rs[wk-1,a,u] for u in UNITS)
   diff=h_strength-a_strength
   metrics[model]["margin"].append((diff,margin))
   if margin!=0:metrics[model]["win"].append((diff,1 if margin>0 else 0))
out={"description":"2025 pregame-safe held-out forward validation of *four-unit component* under three settings; NOT a validation of the full 25/35/25/15 BetWise ranking.","evaluation":"Week >=3; ratings frozen after previous week; raw observed game unit statistics normalized only on games from preceding weeks; excludes FCS games.","results":{}}
for model,scores in metrics.items():
 out["results"][model]={"units":{u:{"n":len(scores[u]),"pearson":round_or_none(pearson(scores[u]))} for u in UNITS},
 "mean_unit_pearson":round_or_none(statistics.fmean(pearson(scores[u]) for u in UNITS)),
 "game_margin":{"n":len(scores["margin"]),"pearson":round_or_none(pearson(scores["margin"]))},
 "game_win":{"n":len(scores["win"]),"auc":round_or_none(auc(scores["win"]))}}
out["limitations"]=["Shared forward games and overlapping weekly training samples mean tiny differences require additional season-level uncertainty evaluation.","Market, ATS and quality-of-competition components are not pregame reconstructed; comparison is for units only, not overall dominance.","Past FBS games with missing advanced stats excluded; verify coverage and provider filtering.","2025 data was used to choose candidate curves, so confirmation on an untouched season is necessary before claiming superiority."]
(P/"stronger_suppression_2025_forward_validation.json").write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2),flush=True)
