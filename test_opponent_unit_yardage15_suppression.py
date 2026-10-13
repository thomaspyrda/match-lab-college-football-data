#!/usr/bin/env python3
"""Research-only suppression of positive game-level four-unit evidence.
Pregame opponent-specific ranks are frozen prior-week validated unit ratings.
Top25 unaffected; ranks 26..136 get quadratic discount; negative evidence never discounted.
No SOS / wins / market adjustments; no baseline or live-file changes.
"""
import csv,json,math,statistics
from pathlib import Path
from collections import defaultdict
K=("PO","PD","RO","RD")
OPP={"PO":"PD","PD":"PO","RO":"RD","RD":"RO"}
METRICS={"PO":[("passing_ppa",.35),("passing_success",.35),("passing_20plus_rate",.15),("passing_yards_per_game",.10),("passing_yards_per_play",.05)],
"PD":[("passing_ppa",.35),("passing_success",.35),("passing_20plus_rate",.15),("passing_yards_per_game",.10),("passing_yards_per_play",.05)],
"RO":[("rushing_success",.22),("rushing_ppa",.18),("stuff_avoidance",.14),("line_yards",.12),("power_success",.10),("second_level_yards",.06),("open_field_yards",.03),("rushing_yards_per_game",.10),("rushing_yards_per_play",.05)],
"RD":[("rushing_success",.22),("rushing_ppa",.18),("stuff_avoidance",.14),("line_yards",.12),("power_success",.10),("second_level_yards",.06),("open_field_yards",.03),("rushing_yards_per_game",.10),("rushing_yards_per_play",.05)]}
AMPS=(0.,1.)
def number(v):
 try:
  x=float(v)
  return x if math.isfinite(x) else None
 except (ValueError,TypeError):return None
def zdist(seq):
 vals=list(seq)
 return statistics.fmean(vals),statistics.pstdev(vals) or 1.
ANCHORS=((40,0.05),(50,0.075),(60,0.10),(70,0.125),(80,0.15),(90,0.20),(100,0.25),(110,0.30),(120,0.35),(130,0.40),(136,0.45))
def custom_suppression(rank):
 if rank is None or rank<=25:return 0.
 if rank<=39:return 0.03
 for i,(edge,value) in enumerate(ANCHORS):
  if rank<=edge:
   if i==0:return value
   left,prior=ANCHORS[i-1]
   return prior+(value-prior)*(rank-left)/(edge-left)
 return 0.45
def factor(rank,amp):
 return 1.-amp*custom_suppression(rank)
def add_yardage_fields(records,season):
 # Use game-level play-by-play with CFBD /plays stored only in workflow retrieval.
 # Exact passing/rushing yards and qualifying plays must be reconstructed before ratings.
 from pathlib import Path
 p=Path("data/research")/str(season)/"unit_yardage_per_game.csv"
 if not p.exists():raise RuntimeError("Missing verified play-by-play yardage source "+str(p))
 import csv
 lookup={(r["game_id"],r["team"]):r for r in csv.DictReader(p.open())}
 for r in records:
  source=lookup.get((r["game_id"],r["team"]))
  if not source:raise RuntimeError("Missing yardage data "+str((season,r["game_id"],r["team"])))
  for side in ("off","def"):
   for kind in ("passing","rushing"):
    for metric in ("yards_per_game","yards_per_play"):
     k=f"{side}_{kind}_{metric}"
     if source.get(k) in (None,""):raise RuntimeError("Missing "+k)
     r[k]=source[k]

def execute(year):
 d=Path("data/research")/str(year)
 members=json.loads((d/"conference_membership.json").read_text())["teams"]
 teams=sorted(members)
 source=list(csv.DictReader((d/"weekly_team_metrics.csv").open()))
 source=[g for g in source if g["fbs_opponent"]=="1" and g["team"] in members and g["opponent"] in members]
 add_yardage_fields(source,year)
 weeks=sorted({int(g["week"]) for g in source})
 frozen=list(csv.DictReader((d/"validated_weighted_weekly_four_unit_strength.csv").open()))
 previous={(int(r["through_week"]),r["team"]):r for r in frozen}
 assert len(previous)==len(teams)*len(weeks)
 pa=list(csv.DictReader((d/"ppa_denominator_audit.csv").open()))
 denom={(int(r["week"]),r["team"],r["opponent"],r["side"],r["kind"]):int(round(float(r["implied_plays"]))) for r in pa if r["integer_consistent"]=="1"}
 snapshots=[]; audits=[]; discrepancies=[]
 for wk in weeks:
  history=[g for g in source if int(g["week"])<=wk]
  # Week-specific normalization uses only games completed by snapshot week.
  scales={}
  for side in ("off","def"):
   for metric in {x for spec in METRICS.values() for x,_ in spec}:
    vals=[number(g.get(f"{side}_{metric}")) for g in history]
    vals=[v for v in vals if v is not None]
    if len(vals)>=20:scales[side,metric]=zdist(vals)
  for amp in AMPS:
   evidence=defaultdict(lambda:defaultdict(list));observations=defaultdict(lambda:defaultdict(int))
   for g in history:
    t,o=g["team"],g["opponent"]
    gw=int(g["week"])
    for unit in K:
     opposing=OPP[unit]
     # Week 1 receives no fabricated previous-season reference: neutral.
     prior=previous.get((gw-1,o))
     rank=int(prior[opposing+"_rank"]) if prior else None
     side="off" if unit in ("PO","RO") else "def"
     terms=[]
     for metric,weight in METRICS[unit]:
      val=number(g.get(f"{side}_{metric}"))
      if val is None or (side,metric) not in scales:continue
      mu,sd=scales[side,metric]
      terms.append((((val-mu)/sd)*(-1 if side=="def" else 1),weight))
     if not terms:continue
     raw=sum(z*w for z,w in terms)/sum(w for _,w in terms)
     multiplier=factor(rank,amp) if raw>0 else 1.
     adjusted=raw*multiplier
     kind="passing" if unit in ("PO","PD") else "rushing"
     n=denom.get((gw,t,o,side,kind))
     if not n:raise RuntimeError(f"Missing validated denominator {year} {gw} {t} {o} {unit}")
     evidence[t][unit].append((adjusted,n))
     observations[t][unit]+=1
     if amp==1.:
      audits.append({"season":year,"snapshot_week":wk,"game_week":gw,"team":t,"opponent":o,"unit":unit,"opposing_unit":opposing,"pregame_opponent_unit_rank":rank if rank else "unavailable_week1","raw_unit_z":round(raw,6),"suppression_multiplier":round(multiplier,6),"adjusted_unit_z":round(adjusted,6),"eligible_plays":n})
   values=defaultdict(dict)
   for t in teams:
    for unit in K:
     e=evidence[t][unit]
     mean=sum(x*n for x,n in e)/sum(n for _,n in e) if e else 0.
     values[t][unit]=mean*len(e)/(len(e)+2) if e else 0.
   for unit in K:
    mu,sd=zdist([values[t][unit] for t in teams])
    ordered=sorted(teams,key=lambda t:(-values[t][unit],t))
    ranks={t:i+1 for i,t in enumerate(ordered)}
    for t in teams:
     snapshots.append({"season":year,"through_week":wk,"valid_from_week":wk+1,"max_suppression":amp,"team":t,"unit":unit,"rank":ranks[t],"rating":round(50+15*(values[t][unit]-mu)/sd,3),"z":round((values[t][unit]-mu)/sd,6),"games":observations[t][unit]})
  if wk==weeks[-1]:
   priorrows={t:previous[wk,t] for t in teams}
   for unit in K:
    for t in teams:
     row=next(r for r in snapshots if r["through_week"]==wk and r["max_suppression"]==0 and r["team"]==t and r["unit"]==unit)
     discrepancies.append(abs(row["rating"]-float(priorrows[t][unit+"_rating"])))
 assert len(snapshots)==len(teams)*len(weeks)*4*len(AMPS)
 assert all(1<=r["rank"]<=len(teams) for r in snapshots)
 with (d/"opponent_unit_yardage15_suppression_weekly_comparison.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(snapshots[0]));w.writeheader();w.writerows(snapshots)
 with (d/"opponent_unit_yardage15_suppression_game_audit.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(audits[0]));w.writeheader();w.writerows(audits)
 meta={"season":year,"team_count":len(teams),"weeks":weeks,"records":len(snapshots),"variants":AMPS,
 "formula":"positive_game_unit_z * [1 - custom_suppression(opponent_pregame_unit_rank)] with 0% for #1-25, 3% for #26-39, and linearly interpolated user anchors #40 to #136; negatives unchanged",
 "user_suppression_anchors":ANCHORS,"week1":"Neutral unadjusted, no pregame prior-week 2025/2026 snapshot available",
 "opposing_unit_map":OPP,"measurement":"Game-level per-metric z standardized from FBS games completed through each snapshot week. Passing and rushing observations weighted by exact validated eligible-play counts. n/(n+2) game-count shrinkage. Independent unit restandardization.",
 "important":"Zero-suppression control is not numerically identical to previous cumulative source-stat unit model, because per-game z normalization differs from cumulative metric normalization. Rank comparisons must use this experiment's zero-suppression control.",
 "zero_suppression_mean_absolute_difference_vs_previous_rating":round(statistics.fmean(discrepancies),3),
 "original_unchanged":True}
 (d/"opponent_unit_yardage15_suppression_metadata.json").write_text(json.dumps(meta,indent=2))
 print("Opponent unit suppression",year,len(snapshots),"unit-team-weeks; MAE control against previous",meta["zero_suppression_mean_absolute_difference_vs_previous_rating"],flush=True)
if __name__=="__main__":
 for y in (2025,2026):execute(y)
