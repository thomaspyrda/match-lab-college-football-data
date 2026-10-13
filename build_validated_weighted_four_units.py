#!/usr/bin/env python3
"""Independent validated-source four-unit weekly ratings (research only).
Uses play-weighted CFBD PPA and success; other metrics from existing game-level
archive. Frozen weekly ranks; no changes to original or live production.
"""
import csv,json,math,statistics
from pathlib import Path
from collections import defaultdict
YEARS=(2025,2026)
K=("PO","PD","RO","RD")
METRICS={
 "PO":[("passing_ppa",.4),("passing_success",.4),("passing_20plus_rate",.2)],
 "PD":[("passing_ppa",.4),("passing_success",.4),("passing_20plus_rate",.2)],
 "RO":[("rushing_success",.25),("rushing_ppa",.2),("stuff_avoidance",.17),("line_yards",.14),("power_success",.11),("second_level_yards",.08),("open_field_yards",.05)],
 "RD":[("rushing_success",.25),("rushing_ppa",.2),("stuff_avoidance",.17),("line_yards",.14),("power_success",.11),("second_level_yards",.08),("open_field_yards",.05)]}
def num(x):
 try:
  v=float(x);return v if math.isfinite(v) else None
 except (TypeError,ValueError):return None
def std(x):
 mu=statistics.fmean(x);return mu,statistics.pstdev(x) or 1.
for year in YEARS:
 d=Path("data/research")/str(year)
 original=list(csv.DictReader((d/"weekly_team_metrics.csv").open()))
 weighted=list(csv.DictReader((d/"reconstructed_weekly_play_weighted_ppa.csv").open()))
 successes=list(csv.DictReader((d/"validated_weekly_play_weighted_success.csv").open()))
 wmap={(int(r["through_week"]),r["team"]):r for r in weighted}
 smap={(int(r["through_week"]),r["team"]):r for r in successes}
 teams=sorted(json.loads((d/"conference_membership.json").read_text())["teams"])
 weeks=sorted({int(r["week"]) for r in original})
 # Cross-check full snapshots; no silent substitution for missing data.
 assert len(wmap)==len(smap)==len(teams)*len(weeks)
 fbs=[r for r in original if r["fbs_opponent"]=="1" and r["team"] in teams and r["opponent"] in teams]
 result=[]
 for wk in weeks:
  history=defaultdict(list)
  for r in fbs:
   if int(r["week"])<=wk:history[r["team"]].append(r)
  raw=defaultdict(dict);missing=[]
  for t in teams:
   for kind in K:
    side="off" if kind in ("PO","RO") else "def"
    component=[]
    for metric,weight in METRICS[kind]:
     if metric.endswith("_ppa"):
      val=num(wmap[wk,t][f"{side}_{metric.split('_')[0]}_ppa_play_weighted"])
     elif metric.endswith("_success"):
      val=num(smap[wk,t][f"{side}_{metric.split('_')[0]}_success_rate"])
     else:
      vals=[num(g.get(f"{side}_{metric}")) for g in history[t]]
      vals=[v for v in vals if v is not None]
      val=statistics.fmean(vals) if vals else None
     if val is not None:component.append((metric,val,weight))
    # Each metric remains independent, calibrated below against team distribution.
    raw[t][kind]=component
    n=len(history[t])
    if n and not component:missing.append((t,kind,wk))
  if missing:raise RuntimeError(f"Missing units {missing[:6]}")
  norm={}
  for kind in K:
   for metric,_ in METRICS[kind]:
    vals=[(t,next((v for m,v,_ in raw[t][kind] if m==metric),None)) for t in teams]
    present=[v for _,v in vals if v is not None]
    if len(present)<20:continue
    mu,sd=std(present)
    norm[kind,metric]=(mu,sd)
  units={}
  for t in teams:
   units[t]={}
   n=len(history[t])
   for kind in K:
    pts=[]
    for metric,val,weight in raw[t][kind]:
     if (kind,metric) not in norm:continue
     mu,sd=norm[kind,metric]
     z=(val-mu)/sd
     pts.append(((-z if kind in ("PD","RD") and metric!="stuff_avoidance" else z),weight))
    composite=sum(x*w for x,w in pts)/sum(w for _,w in pts) if pts else 0.
    units[t][kind]=composite*n/(n+2) if n else 0.
  scaled={}
  for kind in K:
   mu,sd=std([units[t][kind] for t in teams])
   scaled[kind]={t:(units[t][kind]-mu)/sd for t in teams}
  ranked={kind:{t:i+1 for i,t in enumerate(sorted(teams,key=lambda t:(-scaled[kind][t],t)))} for kind in K}
  for t in teams:
   entry={"season":year,"through_week":wk,"valid_from_week":wk+1,"team":t,"fbs_games":len(history[t])}
   for kind in K:
    entry[kind+"_rating"]=round(50+15*scaled[kind][t],3)
    entry[kind+"_z"]=round(scaled[kind][t],6)
    entry[kind+"_rank"]=ranked[kind][t]
   result.append(entry)
 assert len(result)==len(teams)*len(weeks)
 for wk in weeks:
  for kind in K:
   ranks=sorted(x[kind+"_rank"] for x in result if x["through_week"]==wk)
   assert ranks==list(range(1,len(teams)+1))
 with (d/"validated_weighted_weekly_four_unit_strength.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(result[0]));w.writeheader();w.writerows(result)
 summary={"season":year,"teams":len(teams),"weeks":weeks,"rows":len(result),
          "method":"Play-weighted passing/rushing PPA and Success Rate via validated denominators; supporting measures season-to-date equal-game means; per-metric cross-team z-scores; zero-centered sparse-sample shrink n/(n+2), each unit re-standardized",
          "metrics":METRICS,"preserves_existing":True,
          "note":"Research-only source-strength model, no opponent-adjusted scoring, no changes to existing BetWise v1.0 rankings"}
 (d/"validated_weighted_weekly_four_unit_metadata.json").write_text(json.dumps(summary,indent=2))
 print("Validated weighted four-unit rebuild",year,len(result),"records",flush=True)
