#!/usr/bin/env python3
"""Reconstruct exact v5 Team Strength week by week for dominance auditing.\nProduces research-only snapshots; no live ranking files are modified.\n"""
import json, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
EXP=ROOT/"data"/"experiments"
WEEKS=range(2,7)
for week in WEEKS:
    env=os.environ.copy(); env["MODEL_WEEK"]=str(week)
    subprocess.run([sys.executable,str(ROOT/"experiment_expected_performance.py")],env=env,check=True)
weekly={}; teams=set()
for week in WEEKS:
    data=json.loads((EXP/f"recursive_unit_strength_2026_week_{week}.json").read_text())
    weekly[str(week)]={"through_week":week-1,"fbs_teams_ranked":data["fbs_teams_ranked"],"rankings":data["rankings"]}
    teams.update(r["team"] for r in data["rankings"])
trajectories={}
for team in sorted(teams):
    pts=[]
    for week in WEEKS:
        r=next((x for x in weekly[str(week)]["rankings"] if x["team"]==team),None)
        if not r: continue
        pts.append({"pregame_week":week,"through_week":week-1,"rank":r["rank"],
          "overall_team_strength_sd":r["overall_team_strength_sd"],
          "offense_rank":r["offense_rank"],"offensive_strength_sd":r["offensive_strength_sd"],
          "defense_rank":r["defense_rank"],"defensive_strength_sd":r["defensive_strength_sd"],
          "games":r["games"],"preseason_weight":r["preseason_weight"],
          "offense_categories":r["diagnostics"]["offense_categories"],
          "defense_categories":r["diagnostics"]["defense_categories"]})
    trajectories[team]=pts
payload={"schema_version":"dominance-audit-1.0","season":2026,
 "purpose":"Descriptive week-by-week FBS dominance audit; not a predictive backtest.",
 "methodology":"Exact v5 weights and recursive methodology reconstructed independently at each pregame week.",
 "pregame_weeks":list(WEEKS),"weekly":weekly,"trajectories":trajectories}
out=EXP/"weekly_dominance_audit_2026_weeks_2_6.json"
out.write_text(json.dumps(payload,indent=2)+"\n")
print(f"Wrote {out} with {len(trajectories)} team trajectories.")
