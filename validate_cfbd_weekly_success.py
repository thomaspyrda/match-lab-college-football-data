#!/usr/bin/env python3
"""Validate CFBD game-level pass/rush success denominators and reconstruct weekly rates.
No legacy archive or ratings are overwritten. Denominator derived from totalPPA/ppa.
Strict per-observation integer success-count audit avoids unjustified accuracy claims.
"""
import csv,json,math
from pathlib import Path
from collections import defaultdict
for year in (2025,2026):
 folder=Path("data/research")/str(year)
 metrics=list(csv.DictReader((folder/"weekly_team_metrics.csv").open()))
 audit=list(csv.DictReader((folder/"ppa_denominator_audit.csv").open()))
 games={(r["week"],r["team"],r["opponent"]):r for r in metrics if r["fbs_opponent"]=="1"}
 observed=defaultdict(list); flags=[]
 for a in audit:
  g=games.get((a["week"],a["team"],a["opponent"]))
  if g is None:continue
  side,kind=a["side"],a["kind"]
  success=g.get(f"{side}_{kind}_success")
  try:rate=float(success); n=float(a["implied_plays"])
  except (ValueError,TypeError):
   flags.append({"week":a["week"],"team":a["team"],"opponent":a["opponent"],"side":side,"kind":kind,"status":"missing_success_or_denominator"})
   continue
  valid= a["integer_consistent"]=="1" and 0<=rate<=1 and n>=1 and abs(rate*round(n)-round(rate*round(n)))<=.025
  flags.append({"week":a["week"],"team":a["team"],"opponent":a["opponent"],"side":side,"kind":kind,"status":"validated" if valid else "denominator_mismatch","play_count":int(round(n)),"successful_plays":int(round(rate*round(n))) if valid else "","rate":round(rate,9)})
  if valid:observed[(a["team"],side,kind)].append((int(a["week"]),int(round(n)),int(round(rate*round(n)))))
 members=json.loads((folder/"conference_membership.json").read_text())["teams"]
 weeks=sorted({int(r["week"]) for r in metrics})
 out=[]
 for week in weeks:
  for team in sorted(members):
   row={"season":year,"through_week":week,"team":team}
   for side in ("off","def"):
    for kind in ("passing","rushing"):
     count=[x for x in observed[(team,side,kind)] if x[0]<=week]
     expected=len([r for r in metrics if r["team"]==team and r["fbs_opponent"]=="1" and int(r["week"])<=week])
     plays=sum(x[1] for x in count); wins=sum(x[2] for x in count)
     pre=side+"_"+kind
     row[pre+"_success_rate"]=round(wins/plays,8) if plays and len(count)==expected else ""
     row[pre+"_successful_plays"]=wins if len(count)==expected else ""
     row[pre+"_eligible_plays"]=plays if len(count)==expected else ""
     row[pre+"_verified_games"]=len(count)
     row[pre+"_expected_games"]=expected
   out.append(row)
 with (folder/"validated_weekly_play_weighted_success.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
 with (folder/"success_denominator_validation_audit.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(flags[0]));w.writeheader();w.writerows(flags)
 statuses=defaultdict(int)
 for x in flags:statuses[x["status"]]+=1
 meta={"season":year,"checked_unit_game_rows":len(flags),"statuses":dict(statuses),"team_week_rows":len(out),
   "method":"Pass/rush counts inferred from totalPPA/ppa. A count is accepted only if both that ratio and successRate*play_count are integer-consistent. Cumulative rate = sum(successful plays) / sum(eligible plays), FBS opponents only.",
   "caveats":["Matching integer counts validates internal source consistency, not independent proof of Fourth and Short methodology.","API query excluded garbage-time plays; source pass/rush eligibility rules may differ from public third-party displays.","No weekly values are published when any available FBS game lacks verified counts.","No changes to original four-unit/overall ratings."]}
 (folder/"validated_weekly_success_metadata.json").write_text(json.dumps(meta,indent=2))
 print("Success Rate play counts",year,json.dumps(meta),flush=True)
