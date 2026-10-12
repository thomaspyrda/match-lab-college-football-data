#!/usr/bin/env python3
"""Diagnostic only: game outcomes and earned top-10 win credits for raw-metrics baseline."""
import csv,json,statistics
from collections import defaultdict
from pathlib import Path
D=Path(__file__).resolve().parent/"data"/"research"/"2026"
rows=list(csv.DictReader((D/"weekly_team_metrics.csv").open()))
pregame=list(csv.DictReader((D/"pregame_opponent_exposure.csv").open()))
aliases={"Mississippi":"Ole Miss","Connecticut":"UConn","Texas-San Antonio":"UTSA","San José State":"San Jose State"}
def canon(t):return aliases.get(t,t)
lookup={(p["game_id"],canon(p["team"])):p for p in pregame}
# The existing results-heavy model ranks opponents based on frozen units across
# all FBS teams before each game, not AP rankings or postgame reclassifications.
byweek=defaultdict(dict)
for p in pregame:byweek[int(p["week"])][canon(p["opponent"])]=float(p["pregame_opponent_strength"])
ranks={}
for wk,seen in byweek.items():
    # Pregame snapshots for opponents not present this week are unavailable.
    # Use the full ranking engine's frozen snapshots for exact 136-team ranks
    # in a future archive; these within-week ranks are diagnostic only.
    order=sorted(seen,key=lambda t:(-seen[t],t))
    ranks[wk]={t:i+1 for i,t in enumerate(order)}
audit=[]
watch={"UCLA","Oregon","Texas","Ohio State","Oklahoma","Georgia","Alabama","Kentucky","Florida","Utah","Miami","Notre Dame","BYU","Indiana"}
for g in rows:
    team=canon(g["team"]);opp=canon(g["opponent"])
    if team not in watch:continue
    p=lookup.get((g["game_id"],team))
    if p is None:continue
    tp,op=int(float(g["team_points"])),int(float(g["opponent_points"]))
    f=float(p["pregame_team_strength"]);o=float(p["pregame_opponent_strength"])
    expected=7*(f-o)
    resid=max(-35.,min(35.,tp-op-expected))/35
    # Reproduce win/loss and residual component exactly, but avoid inventing
    # a 136-team top-ten quality bonus from incomplete within-week snapshots.
    base=(1 if tp>op else -1)+.4*resid
    audit.append({"week":int(g["week"]),"team":team,"opponent":opp,"score":f"{tp}-{op}",
      "win":int(tp>op),"pregame_team_strength":round(f,4),"pregame_opponent_strength":round(o,4),
      "expected_margin":round(expected,3),"actual_margin":tp-op,
      "margin_residual":round(resid,4),"result_component_before_top10_bonus":round(base,4),
      "within_week_opponent_order_NOT_national_rank":ranks[int(g["week"])].get(opp),
      "note":"Top-10 victory bonus requires full 136-team pregame snapshot"})
audit.sort(key=lambda x:(x["week"],x["team"]))
with (D/"key_game_results_audit.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
(D/"key_game_results_audit.json").write_text(json.dumps({"caveat":"The current archive lacks all 136 frozen weekly team snapshots, so this audit reports exact pregame opponent strength and margin residual but not the full-model top-10 rank bonus.","games":audit},indent=2))
print("Audit rows:",len(audit))
for x in audit:
    if (x["team"],x["opponent"]) in {("UCLA","Oregon"),("Texas","Ohio State"),("Texas","Oklahoma"),("Oregon","Oklahoma State"),("Georgia","Alabama")}:
        print(x)
