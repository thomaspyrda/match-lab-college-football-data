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
units=defaultdict(lambda: defaultdict(list))
quality=defaultdict(list)
validation=defaultdict(list)
audit=[]
pre={(int(r["week"]),r["team"]):float(r["pregame_strength"]) for r in csv.DictReader((D/"pregame_all_team_ranks.csv").open())}
for r in fbs:
    t=r["team"];o=r["opponent"];wk=int(r["week"])
    pr=ranks.get((wk,o))
    if pr is None:continue
    for k in ("PO","RO","PD","RD"):
        val=m.unit_measure(r,k,scales)
        if val is not None:units[t][k].append((val,max(1,m.num(r.get("plays_count")) or 1)))
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
    quality[t].append((1 if win else -1)+.4*residual)
    tier=(1. if pr<=10 else .6 if pr<=25 else .3 if pr<=50 else 0.)
    if pr<=50:
        ecv=(tier if win else -.15*tier)+.15*residual
    else:
        ecv=-(1. if not win else 0.) + min(0.,residual)*.65
        ecv=min(0.,ecv)
    validation[t].append(max(-1.65,min(1.25,ecv)))
    audit.append({"team":t,"week":wk,"opponent":o,"opponent_pregame_rank":pr,"margin":margin,"quality_component":round(quality[t][-1],4),"ecv_component":round(validation[t][-1],4)})
def z(d):
    mu=statistics.fmean(d.values());sd=statistics.pstdev(d.values()) or 1.
    return {t:(v-mu)/sd for t,v in d.items()}
def meanvals(a):
    return sum(v*w for v,w in a)/sum(w for v,w in a) if a else 0.
# Same four unadjusted units for every variant; apply SOS once to each final unit.
raw={t:{k:meanvals(units[t][k]) for k in ("PO","RO","PD","RD")} for t in m.teams}
q=z({t:statistics.fmean(quality[t]) if quality[t] else -1. for t in m.teams})
e=z({t:statistics.fmean(validation[t]) if validation[t] else 0. for t in m.teams})
sos_z=z({t:exposure.get(t,0.) for t in m.teams})
variants={}
for alpha in (0.,.25,.5):
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
    variants["sos_"+str(alpha).replace(".","p")]=result
(D/"season_aggregate_sos_comparison.json").write_text(json.dumps({"method":"FBS-only full-season raw metrics, grouped into four units; season average pregame opponent strength applied once to all units; 55/30/15 results & ECV","variants":variants},indent=2))
with (D/"season_aggregate_sos_comparison.csv").open("w",newline="") as f:
    w=csv.writer(f);w.writerow(["model","rank","team","score","sos_z","PO","RO","PD","RD"])
    for name,rs in variants.items():
        for r in rs:w.writerow([name,r["rank"],r["team"],r["score"],r["sos_z"],r["PO"],r["RO"],r["PD"],r["RD"]])
print("SOS test",[(name,[(x["rank"],x["team"]) for x in rs[:15]]) for name,rs in variants.items()])
