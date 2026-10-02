#!/usr/bin/env python3
"""Final research-only v15 validation using the exact source fields/model eligibility."""
import json, os, subprocess, sys
from pathlib import Path
from experiment_dominance_v15 import canon
ROOT=Path(__file__).resolve().parent; EXP=ROOT/"data"/"experiments"; WEEKS=range(2,7)
hist=json.loads((ROOT/"data"/"historical"/"2026.json").read_text())["games"]
for week in WEEKS:
    env=os.environ.copy(); env["MODEL_WEEK"]=str(week)
    subprocess.run([sys.executable,str(ROOT/"experiment_dominance_v15.py")],env=env,check=True)
weekly={}; trajectories={}; alerts=[]; safety={}
for week in WEEKS:
    d=json.loads((EXP/f"recursive_unit_strength_v15_2026_week_{week}.json").read_text())
    assert d["pregame_week"]==week and d["through_week"]==week-1
    # v15 reads historical teams from "home"/"away", not "home_team"/"away_team".
    # Count only FBS-vs-FBS source records before MODEL_WEEK. Model counts may be lower
    # when advanced rows are unavailable, but can never be higher.
    model_teams={r["team"] for r in d["rankings"]}; source_counts={}
    eligible=[g for g in hist if g.get("result") and int(g.get("week") or 0)<week]
    for g in eligible:
        h,a=canon(g.get("home","")),canon(g.get("away",""))
        if h in model_teams and a in model_teams:
            source_counts[h]=source_counts.get(h,0)+1; source_counts[a]=source_counts.get(a,0)+1
    violations=[{"team":r["team"],"model_games":r["games"],"source_games_before_week":source_counts.get(r["team"],0)}
                for r in d["rankings"] if r["games"]>source_counts.get(r["team"],0)]
    assert not violations, f"future-game leakage: {violations[:10]}"
    safety[str(week)]={"eligible_source_records":len(eligible),"violations":0}
    weekly[str(week)]={"through_week":week-1,"fbs_teams_ranked":d["fbs_teams_ranked"],"rankings":d["rankings"]}
for week in WEEKS:
    for r in weekly[str(week)]["rankings"]:
        trajectories.setdefault(r["team"],[]).append({"pregame_week":week,"rank":r["rank"],"overall_team_strength_sd":r["overall_team_strength_sd"],
          "offense_rank":r["offense_rank"],"defense_rank":r["defense_rank"],"games":r["games"],"preseason_weight":r["preseason_weight"]})
for team,pts in trajectories.items():
    for a,b in zip(pts,pts[1:]):
        dr=b["rank"]-a["rank"]; ds=b["overall_team_strength_sd"]-a["overall_team_strength_sd"]
        if abs(dr)>=25 or abs(ds)>=1.0: alerts.append({"team":team,"from_week":a["pregame_week"],"to_week":b["pregame_week"],"rank_change":dr,"strength_change_sd":round(ds,3)})
payload={"schema_version":"v15-final-validation-1.0","season":2026,"public_ui":False,
 "pregame_safety":{"rule":"MODEL_WEEK N uses only historical records with result and week < N, matching v15 source fields home/away","weeks":safety},
 "weekly":weekly,"trajectories":trajectories,"large_movement_alerts":sorted(alerts,key=lambda x:abs(x["strength_change_sd"]),reverse=True)}
out=EXP/"v15_final_validation_2026_weeks_2_6.json"; out.write_text(json.dumps(payload,indent=2)+"\n")
print(f"Wrote {out}; pregame safety passed Weeks 2-6; {len(alerts)} large-movement alerts")
