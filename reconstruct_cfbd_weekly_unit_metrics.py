#!/usr/bin/env python3
"""Reconstruct weekly cumulative CFBD game-level unit metrics on research branch.
Explicitly distinguish equal-game means (reproducible) from play-weighted proxies
(approximate; plays_count is all offensive plays, not pass/rush attempts).
Never label these exact Fourth and Short parity or overwrite existing archives.
"""
import csv,json,statistics,math
from collections import defaultdict
from pathlib import Path
YEARS=(2025,2026)
ALIASES={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
METRICS=("passing_ppa","passing_success","rushing_ppa","rushing_success","passing_20plus_rate","line_yards","power_success","stuff_avoidance","second_level_yards","open_field_yards")
def num(x):
 try:
  v=float(x)
  return v if math.isfinite(v) else None
 except (TypeError,ValueError):return None
def avg(xs):
 return statistics.fmean(xs) if xs else None
for year in YEARS:
 folder=Path("data/research")/str(year)
 data=list(csv.DictReader((folder/"weekly_team_metrics.csv").open()))
 members=json.loads((folder/"conference_membership.json").read_text())["teams"]
 teams=sorted(ALIASES.get(t,t) for t in members)
 for r in data:
  for col in ("team","opponent"):r[col]=ALIASES.get(r[col],r[col])
 fbs=[r for r in data if r["fbs_opponent"]=="1" and r["team"] in teams and r["opponent"] in teams]
 weeks=sorted({int(r["week"]) for r in fbs})
 output=[]
 for week in weeks:
  by=defaultdict(list)
  for r in fbs:
   if int(r["week"])<=week:by[r["team"]].append(r)
  for team in teams:
   games=by[team];out={"season":year,"through_week":week,"team":team,"fbs_games":len({g["game_id"] for g in games})}
   for side in ("off","def"):
    for metric in METRICS:
     key=side+"_"+metric
     values=[num(r.get(key)) for r in games]
     valid=[x for x in values if x is not None]
     out[key+"_equal_game_mean"]=round(avg(valid),8) if valid else ""
     out[key+"_coverage_games"]=len(valid)
   output.append(out)
 assert len(output)==len(teams)*len(weeks)
 for week in weeks:
  assert len([r for r in output if r["through_week"]==week])==len(teams)
 path=folder/"reconstructed_weekly_unit_source_metrics.csv"
 with path.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
 (folder/"reconstructed_weekly_unit_source_metadata.json").write_text(json.dumps({
 "season":year,"source":"Existing CFBD /stats/game/advanced game-level archive","excluded_opponents":"FCS opponents excluded",
 "garbage_time":"Original archive requested excludeGarbageTime=true",
 "method":"Cumulative arithmetic mean of per-game CFBD metric values, calculated independently at each completed week",
 "important_limitation":"Passing/rushing success rates and PPA are equal-game averages, NOT exact play-weighted season aggregates; source does not preserve eligible pass/rush play denominators. Do not claim parity with Fourth and Short.",
 "validation":{"teams":len(teams),"weeks":len(weeks),"team_week_rows":len(output),"fbs_game_rows":len(fbs)},
 "preserved":"All original unit and overall rankings remain unchanged"
 },indent=2))
 print("Reconstructed CFBD weekly source metrics",year,"teams",len(teams),"weeks",len(weeks),"rows",len(output),flush=True)
