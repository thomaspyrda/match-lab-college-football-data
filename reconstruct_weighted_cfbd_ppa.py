#!/usr/bin/env python3
"""Research only: derive PPA-implied pass/rush denominators and weighted weekly metrics.
Does not overwrite original four-unit or dominance ratings.
"""
import csv,json,math,statistics
from pathlib import Path
from collections import defaultdict
for year in (2025,2026):
 d=Path("data/research")/str(year)
 records=list(csv.DictReader((d/"weekly_team_metrics.csv").open()))
 members=set(json.loads((d/"conference_membership.json").read_text())["teams"])
 games=[r for r in records if r["fbs_opponent"]=="1" and r["team"] in members and r["opponent"] in members]
 weeks=sorted({int(g["week"]) for g in games})
 by=defaultdict(list)
 for g in games:by[g["team"]].append(g)
 out=[];audit=[]
 def n(v):
  try:
   x=float(v);return x if math.isfinite(x) else None
  except (ValueError,TypeError):return None
 for g in games:
  for side in ("off","def"):
   for kind in ("passing","rushing"):
    prefix=f"{side}_{kind}"
    ppa=n(g.get(prefix+"_ppa"));total=n(g.get(prefix+"_total_ppa"))
    derived=total/ppa if ppa is not None and total is not None and abs(ppa)>0.000001 else None
    ok=derived is not None and derived>0 and derived<1000 and abs(derived-round(derived))<.025
    audit.append({"season":year,"week":g["week"],"team":g["team"],"opponent":g["opponent"],"side":side,"kind":kind,"mean_ppa":ppa,"total_ppa":total,"implied_plays":round(derived,5) if derived is not None else "","integer_consistent":int(ok)})
 lookup={(r["week"],r["team"],r["side"],r["kind"]):r for r in audit}
 for wk in weeks:
  for team in sorted(members):
   rows=[g for g in by[team] if int(g["week"])<=wk]
   result={"season":year,"through_week":wk,"team":team,"fbs_games":len(rows)}
   for side in ("off","def"):
    for kind in ("passing","rushing"):
     vals=[];unweighted=[]
     for g in rows:
      p=n(g.get(f"{side}_{kind}_ppa"))
      if p is None:continue
      unweighted.append(p)
      a=lookup[g["week"],team,side,kind]
      if a["integer_consistent"]:vals.append((p,round(a["implied_plays"])))
     prefix=f"{side}_{kind}"
     result[prefix+"_ppa_game_mean"]=round(statistics.fmean(unweighted),7) if unweighted else ""
     result[prefix+"_ppa_play_weighted"]=round(sum(p*w for p,w in vals)/sum(w for _,w in vals),7) if vals and len(vals)==len(unweighted) else ""
     result[prefix+"_weighted_games"]=len(vals)
     result[prefix+"_available_games"]=len(unweighted)
   out.append(result)
 target=d/"reconstructed_weekly_play_weighted_ppa.csv"
 with target.open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
 with (d/"ppa_denominator_audit.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(audit[0]));w.writeheader();w.writerows(audit)
 meta={"season":year,"team_weeks":len(out),"games":len(games),"audit_rows":len(audit),"usable_integer_denominators":sum(x["integer_consistent"] for x in audit),"method":"totalPPA / ppa; only accepted when implied count is within .025 of positive integer and <1000; report play-weighted PPA only when all available FBS games validate","limits":"No exact success-rate play weights unless same denominators and success play definitions validated. Does not independently prove Fourth and Short parity. Defensive records mirror opponent offense and may show the same observation twice.","preserve_original":True}
 (d/"ppa_denominator_audit_metadata.json").write_text(json.dumps(meta,indent=2))
 print("PPA denominator audit",json.dumps(meta),flush=True)
