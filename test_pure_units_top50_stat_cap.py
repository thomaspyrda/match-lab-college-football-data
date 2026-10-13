#!/usr/bin/env python3
"""Isolated test: season-aggregated raw unit stats, single season SOS adjustment, earned results."""
import csv,json,statistics,math
from collections import defaultdict
from pathlib import Path
import run_four_unit_research as m
D=m.FOLDER
ranks={(int(r["week"]),r["team"]):int(r["pregame_rank"]) for r in csv.DictReader((D/"pregame_all_team_ranks.csv").open())}
exposure={r["team"]:float(r["pregame_opponent_strength"]) for r in csv.DictReader((D/"pregame_exposure_summary.csv").open()) if r["pregame_opponent_strength"] not in ("",None)}
# Team rows and metric normalization refer only to completed games through this week;
# FCS games do not contribute to four-unit measurements or opponent exposure.
fbs=[r for r in m.rows if int(r["fbs_opponent"]) and r["opponent"] in m.teams]
scales=m.perweek_metric_z(fbs)
for side in ("off","def"):
    vals=[m.num(r.get(side+"_passing_20plus_rate")) for r in fbs]
    vals=[v for v in vals if v is not None]
    if len(vals)<10:raise ValueError("Insufficient 20+ yard pass-rate observations: "+side)
    scales[(side,"passing_20plus_rate")]=(statistics.fmean(vals),statistics.pstdev(vals) or 1.)
# Seven rushing-only measures, user-prioritized; no shared scoring or passing.
RUSH_WEIGHTS={"rushing_success":.25,"rushing_ppa":.20,"stuff_avoidance":.17,
              "line_yards":.14,"power_success":.11,"second_level_yards":.08,
              "open_field_yards":.05}
def pure_rush_measure(row,kind):
    side="off" if kind=="RO" else "def"
    values=[]
    for metric,weight in RUSH_WEIGHTS.items():
        key=(side,metric)
        val=m.num(row.get(side+"_"+metric))
        if val is None or key not in scales:continue
        mu,sd=scales[key]
        x=(val-mu)/sd
        if side=="def":x=-x
        values.append((x,weight))
    return sum(x*w for x,w in values)/sum(w for _,w in values) if values else None
# Passing units contain only pass-specific PPA, success and explosive-play measures.
PASS_WEIGHTS={"passing_ppa":.40,"passing_success":.40,"passing_20plus_rate":.20}
def pure_pass_measure(row,kind):
    side="off" if kind=="PO" else "def"
    values=[]
    for metric,weight in PASS_WEIGHTS.items():
        key=(side,metric)
        val=m.num(row.get(side+"_"+metric))
        if val is None or key not in scales:continue
        mu,sd=scales[key]
        z=(val-mu)/sd
        if side=="def":z=-z
        values.append((z,weight))
    return sum(z*w for z,w in values)/sum(w for _,w in values) if values else None
units=defaultdict(lambda: defaultdict(list))
# Frozen pregame opponent-strength proxy for expected unit performance.
# Expected standardized unit value = -0.50 * opponent's strength z-score.
# Unit residual = actual minus expected (positive only if beating expectation).
PREGAME_EXPECTATION_BETA=.50

results_events=defaultdict(list)
validation=defaultdict(list)
audit=[]
pre={(int(r["week"]),r["team"]):float(r["pregame_strength"]) for r in csv.DictReader((D/"pregame_all_team_ranks.csv").open())}
pregame_by_week=defaultdict(dict)
for (wk,t),strength in pre.items(): pregame_by_week[wk][t]=strength
pregame_week_z={}
for wk,ts in pregame_by_week.items():
    mu=statistics.fmean(ts.values());sd=statistics.pstdev(ts.values()) or 1.
    for t,s in ts.items():pregame_week_z[(wk,t)]=(s-mu)/sd
game_audit=[]
for r in fbs:
    t=r["team"];o=r["opponent"];wk=int(r["week"])
    pr=ranks.get((wk,o))
    if pr is None:continue
    for k in ("PO","RO","PD","RD"):
        val=pure_rush_measure(r,k) if k in ("RO","RD") else pure_pass_measure(r,k)
        if val is not None:
            expected=-PREGAME_EXPECTATION_BETA*pregame_week_z[(wk,o)]
            residual_unit=val-expected
            # Strict evidence rule: positive standardized statistical residuals
            # earn no credit outside frozen pregame Top 50; negatives remain.
            if pr>50:residual_unit=min(0.,residual_unit)
            units[t][k].append((residual_unit,max(1,m.num(r.get("plays_count")) or 1)))
            if t in ("Georgia State","Oregon State"):
                game_audit.append({"team":t,"week":wk,"opponent":o,"unit":k,
                  "actual":round(val,4),"expected":round(expected,4),
                  "above_expectation":round(residual_unit,4)})
    ownrank=ranks.get((wk,t))
    # Pregame margin is based on the frozen team/opponent strength snapshot.
    # This matches existing result-vs-expectation design; actual raw scores are never SOS-adjusted.
    pregame=dict()
    # Link frozen strengths by team and week using exported national snapshots.
    pregame_t=pre[(wk,t)];pregame_o=pre[(wk,o)]
    expected=7*(pregame_t-pregame_o)
    margin=float(r["team_points"])-float(r["opponent_points"])
    residual=max(-1.,min(1.,(margin-expected)/35.))
    win=margin>0
    # Wins over opponents outside the frozen pregame Top 30 provide zero
    # positive QoR credit. Preserve downside for underperformance and all losses.
    # Earned quality victories are separate from universal loss penalties.
    # No positive QoR reward for wins beyond the frozen pregame Top 30.
    earned=(1. if pr<=10 else .6 if pr<=25 else .3 if pr<=30 else 0.) if win else 0.
    downside=min(0.,.4*residual) if win else .4*residual
    results_events[t].append((earned,not win,downside))
    tier=(1. if pr<=10 else .6 if pr<=25 else .3 if pr<=30 else 0.)
    if pr<=30:
        ecv=(tier if win else -.15*tier)+.15*residual
    else:
        ecv=-(1. if not win else 0.) + min(0.,residual)*.65
        ecv=min(0.,ecv)
    validation[t].append(max(-1.65,min(1.25,ecv)))
    audit.append({"team":t,"week":wk,"opponent":o,"opponent_pregame_rank":pr,"margin":margin,"earned_win_credit":earned,"loss":not win,"downside":round(downside,4),"ecv_component":round(validation[t][-1],4)})
def z(d):
    mu=statistics.fmean(d.values());sd=statistics.pstdev(d.values()) or 1.
    return {t:(v-mu)/sd for t,v in d.items()}
def meanvals(a):
    return sum(v*w for v,w in a)/sum(w for v,w in a) if a else 0.
# Same four unadjusted units for every variant; apply SOS once to each final unit.
raw={t:{k:meanvals(units[t][k]) for k in ("PO","RO","PD","RD")} for t in m.teams}
# Calculate per-game credit and punishment separately, then standardize the
# combined results component. Every loss is penalized regardless of SOS.
def quality_for(loss_cost):
    return z({t:(statistics.fmean(earned-loss_cost*loss+downside for earned,loss,downside in results_events[t])
       if results_events[t] else -loss_cost) for t in m.teams})
e=z({t:statistics.fmean(validation[t]) if validation[t] else 0. for t in m.teams})
sos_z=z({t:exposure.get(t,0.) for t in m.teams})
variants={}
for loss_cost in (1.5,):
  q=quality_for(loss_cost)
  for alpha in (0.,):
      # Season SOS adjusts all four standardized performance units equally.
      # No separate conference bonus. A positive SOS means harder opponents.
      adjusted={t:{k:raw[t][k]+alpha*sos_z[t] for k in ("PO","RO","PD","RD")} for t in m.teams}
      stat_z=z({t:statistics.fmean(adjusted[t].values()) for t in m.teams})
      result=[]
      for t in m.teams:
          score=.55*stat_z[t]+.30*q[t]+.15*e[t]
          result.append({"team":t,"score":round(score,5),"unadjusted_units":round(statistics.fmean(raw[t].values()),5),
            "sos_z":round(sos_z[t],4),"quality_z":round(q[t],4),"validation_z":round(e[t],4),
            **{k:round(adjusted[t][k],5) for k in ("PO","RO","PD","RD")}})
      result.sort(key=lambda x:(-x["score"],x["team"]))
      for i,v in enumerate(result,1):v["rank"]=i
      variants["loss_"+str(loss_cost).replace(".","p")+"_sos_"+str(alpha).replace(".","p")]=result
(D/"pure_units_top50_stat_cap_comparison.json").write_text(json.dumps({"method":"FBS-only pure 3-metric passing PO/PD (40/40/20, 20+ yard play-rate definition); pure 7-metric rushing RO/RD; season average pregame opponent strength applied once; 55/30/15 Top30 earned wins, 1.5x universal loss penalties; actual minus expected unit score; zero positive unit evidence outside pregame Top 50","variants":variants},indent=2))
with (D/"pure_units_top50_stat_cap_comparison.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["model","rank","team","score","sos_z","PO","RO","PD","RD"])
    for name,rs in variants.items():
        for r in rs:w.writerow([name,r["rank"],r["team"],r["score"],r["sos_z"],r["PO"],r["RO"],r["PD"],r["RD"]])
print("SOS test",[(name,[(x["rank"],x["team"]) for x in rs[:15]]) for name,rs in variants.items()])

(D/"pure_units_top50_stat_cap_audit.json").write_text(json.dumps(game_audit,indent=2))
