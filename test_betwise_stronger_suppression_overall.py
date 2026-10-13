#!/usr/bin/env python3
"""2026 25/35/25/15 overall comparison using custom adjusted Week6 units only.
Keep preserved baseline competition/market/results; do not double-apply frozen 2025 unit betas.
"""
import csv,json,statistics
from pathlib import Path
import test_betwise_2025_coefficients_on_2026 as old
D=Path("data/research/2026")
data=list(csv.DictReader((D/"opponent_unit_stronger_suppression_weekly_comparison.csv").open()))
latest=max(int(r["through_week"]) for r in data)
parts={(r["team"],r["unit"]):float(r["z"]) for r in data if int(r["through_week"])==latest and float(r["max_suppression"])==1.}
teams=old.current.teams
assert len(parts)==len(teams)*4,(len(parts),len(teams))
base=old.current.base
four=base.standardize({t:statistics.fmean(parts[t,k] for k in ("PO","PD","RO","RD")) for t in teams})
baseline={r["team"]:r for r in old.rows}
rows=[]
for t in teams:
 score=.25*four[t]+.35*base.competition[t]+.25*base.market_strength_with_residual[t]+.15*base.results[t]
 rows.append({"team":t,"rating":round(50+15*score,2),"score_z":round(score,6),"four_unit_component_z":round(four[t],5),"competition_component_z":round(base.competition[t],5),"market_component_z":round(base.market_strength_with_residual[t],5),"results_component_z":round(base.results[t],5),**{k+"_z":round(parts[t,k],6) for k in ("PO","PD","RO","RD")}})
rows.sort(key=lambda x:(-x["score_z"],x["team"]))
for i,r in enumerate(rows,1):
 r["rank"]=i;r["baseline_rank"]=baseline[r["team"]]["rank"];r["rank_change"]=r["baseline_rank"]-i;r["baseline_rating"]=baseline[r["team"]]["dominance_index"]
report={"season":2026,"through_week":latest,"model":"Research-only 3%-45% opposing unit suppression overall dominance","weights":{"four_units":.25,"competition":.35,"market_ats":.25,"results":.15},"explanation":"Use latest frozen-week adjusted unit z ratings, average PO/PD/RO/RD then restandardize nationally. Original preserved v1.0 competition, market+ATS, results components reused; 2025 opponent-unit beta not reapplied, to avoid double opponent adjustment.","limitations":["This is a component substitution experiment, not calibrated final v1.0; underlying new unit z scores use different weighting/normalization from the original.","Historical season reference ratings use preceding weeks; Week 1 unadjusted.","Not a next-game prediction or statistically validated superiority.","Production and original baseline unchanged."],"rows":rows}
(D/"betwise_stronger_suppression_overall_comparison.json").write_text(json.dumps(report,indent=2))
with (D/"betwise_stronger_suppression_overall_comparison.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print("Top25 updated BetWise",[(r["rank"],r["team"],r["rating"],r["baseline_rank"]) for r in rows[:25]],flush=True)
