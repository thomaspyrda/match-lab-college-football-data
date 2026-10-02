#!/usr/bin/env python3
"""Final research-only v14 validation: reconstruct pregame Weeks 2-6 and audit movement."""
import json, os, subprocess, sys, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parent; EXP=ROOT/"data"/"experiments"; WEEKS=range(2,7)
for week in WEEKS:
    env=os.environ.copy();env["MODEL_WEEK"]=str(week)
    subprocess.run([sys.executable,str(ROOT/"experiment_dominance_v14.py")],env=env,check=True)
weekly={}; trajectories={}; alerts=[]
for week in WEEKS:
    p=EXP/f"recursive_unit_strength_v14_2026_week_{week}.json"; d=json.loads(p.read_text())
    assert d["pregame_week"]==week and d["through_week"]==week-1
    assert all(r["games"]<=week-1 for r in d["rankings"]), "future-game leakage in qualifying game count"
    weekly[str(week)]={"through_week":week-1,"fbs_teams_ranked":d["fbs_teams_ranked"],"rankings":d["rankings"]}
for week in WEEKS:
    for r in weekly[str(week)]["rankings"]:
        trajectories.setdefault(r["team"],[]).append({"pregame_week":week,"rank":r["rank"],"overall_team_strength_sd":r["overall_team_strength_sd"],
          "offense_rank":r["offense_rank"],"defense_rank":r["defense_rank"],"games":r["games"],"preseason_weight":r["preseason_weight"]})
for team,pts in trajectories.items():
    for a,b in zip(pts,pts[1:]):
        dr=b["rank"]-a["rank"]; ds=b["overall_team_strength_sd"]-a["overall_team_strength_sd"]
        if abs(dr)>=25 or abs(ds)>=1.0: alerts.append({"team":team,"from_week":a["pregame_week"],"to_week":b["pregame_week"],"rank_change":dr,"strength_change_sd":round(ds,3)})
payload={"schema_version":"v14-final-validation-1.0","season":2026,"public_ui":False,
 "pregame_safety":{"rule":"MODEL_WEEK N uses games with week < N","asserted_through_week_matches":True,"asserted_qualifying_games_lte_prior_weeks":True},
 "weekly":weekly,"trajectories":trajectories,"large_movement_alerts":sorted(alerts,key=lambda x:abs(x["strength_change_sd"]),reverse=True)}
out=EXP/"v14_final_validation_2026_weeks_2_6.json";out.write_text(json.dumps(payload,indent=2)+"\n");print(f"Wrote {out}; {len(alerts)} large-movement alerts")
