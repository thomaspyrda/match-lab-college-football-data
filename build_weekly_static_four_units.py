#!/usr/bin/env python3
"""Frozen end-of-week FBS-only four-unit ratings (research only).
Each week's model uses only game rows from that season through that week.
Not BetWise v1 season-final ratings; no market/results/conference prior.
"""
import csv,json,statistics,os
from collections import defaultdict
from pathlib import Path
SEASONS=(2025,2026)
K=("PO","PD","RO","RD")
METRICS={
 "PO":[("passing_ppa",.4),("passing_success",.4),("passing_20plus_rate",.2)],
 "PD":[("passing_ppa",.4),("passing_success",.4),("passing_20plus_rate",.2)],
 "RO":[("rushing_success",.25),("rushing_ppa",.20),("stuff_avoidance",.17),
       ("line_yards",.14),("power_success",.11),("second_level_yards",.08),("open_field_yards",.05)],
 "RD":[("rushing_success",.25),("rushing_ppa",.20),("stuff_avoidance",.17),
       ("line_yards",.14),("power_success",.11),("second_level_yards",.08),("open_field_yards",.05)]
}
ALIASES={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def canon(s):return ALIASES.get(s,s)
def numeric(x):
 try:return float(x) if x not in ("",None) else None
 except (ValueError,TypeError):return None
def meanstd(xs):
 return statistics.fmean(xs),statistics.pstdev(xs) or 1.
def build(season):
 folder=Path("data/research")/str(season)
 source=folder/"weekly_team_metrics.csv"
 data=list(csv.DictReader(source.open()))
 for r in data:
  r["team"]=canon(r["team"]);r["opponent"]=canon(r["opponent"])
 # All known FBS teams, including teams currently on bye.
 members=json.loads((folder/"conference_membership.json").read_text())["teams"]
 teams=sorted(canon(x) for x in members)
 teams=set(teams)
 fbs=[r for r in data if str(r["fbs_opponent"])=="1" and r["team"] in teams and r["opponent"] in teams]
 weeks=sorted(set(int(r["week"]) for r in fbs))
 assert len(teams)>=130 and fbs and weeks,(season,len(teams),len(fbs))
 unit_rows=[]; opponent_rows=[]
 for week in weeks:
  current=[r for r in fbs if int(r["week"])<=week]
  # Standardize game observations against the season-to-date only.
  norm={}
  for side in ("off","def"):
   for name in {m for spec in METRICS.values() for m,_ in spec}:
    values=[numeric(r.get(side+"_"+name)) for r in current]
    values=[v for v in values if v is not None]
    if len(values)>=10:norm[side,name]=meanstd(values)
  sums=defaultdict(lambda:defaultdict(list))
  counts=defaultdict(set)
  for r in current:
   t=r["team"];counts[t].add(r["game_id"])
   plays=max(1.,numeric(r.get("plays_count")) or 1.)
   for unit in K:
    side="off" if unit in ("PO","RO") else "def"
    points=[]
    for metric,w in METRICS[unit]:
     v=numeric(r.get(side+"_"+metric))
     if v is None or (side,metric) not in norm:continue
     mu,sd=norm[side,metric]
     z=(v-mu)/sd
     points.append(((z if side=="off" else -z),w))
    if points:sums[t][unit].append((sum(z*w for z,w in points)/sum(w for z,w in points),plays))
  # Empirical Bayes shrink-to-average for sparse schedules: n/(n+2).
  raw={}
  for t in teams:
   raw[t]={}
   for unit in K:
    seq=sums[t][unit]
    avg=sum(v*w for v,w in seq)/sum(w for _,w in seq) if seq else 0.
    n=len(seq)
    raw[t][unit]=avg*n/(n+2) if n else 0.
  standardized={}
  for unit in K:
   mu,sd=meanstd([raw[t][unit] for t in teams])
   standardized[unit]={t:(raw[t][unit]-mu)/sd for t in teams}
  week_ranks={}
  for unit in K:
   ordered=sorted(teams,key=lambda t:(-standardized[unit][t],t))
   week_ranks[unit]={t:i+1 for i,t in enumerate(ordered)}
  for t in sorted(teams):
   out={"season":season,"through_week":week,"valid_from_week":week+1,"team":t,"fbs_games":len(counts[t])}
   for unit in K:
    out[unit+"_z"]=round(standardized[unit][t],6)
    out[unit+"_rating"]=round(50+15*standardized[unit][t],3)
    out[unit+"_rank"]=week_ranks[unit][t]
    out[unit+"_sample_games"]=len(sums[t][unit])
   unit_rows.append(out)
  for r in fbs:
   if int(r["week"])!=week+1:continue
   team=r["team"];opp=r["opponent"]
   out={"season":season,"game_week":week+1,"snapshot_through_week":week,
        "game_id":r["game_id"],"team":team,"opponent":opp}
   for unit in K:
    out["opponent_"+unit+"_rank"]=week_ranks[unit][opp]
    out["opponent_"+unit+"_rating"]=round(50+15*standardized[unit][opp],3)
   opponent_rows.append(out)
 # Also export every game's opponent snapshots from the previous week where available.
 assert len(unit_rows)==len(teams)*len(weeks)
 for unit in K:
  for week in weeks:
   subset=[x[unit+"_rank"] for x in unit_rows if x["through_week"]==week]
   assert sorted(subset)==list(range(1,len(teams)+1))
 path=folder/"weekly_static_four_unit_strength.csv"
 with path.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(unit_rows[0]));w.writeheader();w.writerows(unit_rows)
 if opponent_rows:
  path2=folder/"pregame_static_four_unit_opponents.csv"
  with path2.open("w",newline="") as f:
   w=csv.DictWriter(f,fieldnames=list(opponent_rows[0]));w.writeheader();w.writerows(opponent_rows)
 summary={"season":season,"method":"cumulative FBS-only game metrics standardized using observations available through each week; sample count shrinkage n/(n+2); no market, win or opponent adjustments","metric_definitions":METRICS,
  "rating_scale":"50+15*z by unit per week, unbounded","weekly_team_rows":len(unit_rows),
  "pregame_opponent_rows":len(opponent_rows),"teams":len(teams),"weeks":weeks,
  "caveats":["A rating's week W can be used only from week W+1 onward.","Each unit is estimated from that unit's own game statistics, not opponents' final ratings.","Missing teams are shrunk to national-average raw unit performance, not assigned fabricated observations.","No preseason ratings are supplied for the first week; do not use later weekly strength retroactively.","This independent stat-only snapshot is not the finalized production Team Dominance model."]}
 (folder/"weekly_static_four_unit_metadata.json").write_text(json.dumps(summary,indent=2))
 print("Weekly four-unit ratings",season,len(unit_rows),"team-weeks",len(opponent_rows),"next-week opponent records")
if __name__=="__main__":
 for s in SEASONS:build(s)
