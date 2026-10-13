#!/usr/bin/env python3
"""Isolated 2026 comparison: frozen 2025 opponent-unit betas against 2026-fit betas."""
import csv,json,statistics
from collections import defaultdict
from pathlib import Path
import test_betwise_unit_matched as current
D=Path("data/research/2026")
past=json.loads(Path("data/research/2025/betwise_unit_matched_2025_backtest.json").read_text())
old_betas={k:past["coefficients"][k]["adjustment_beta"] for k in current.K}
adjusted=defaultdict(lambda:defaultdict(list))
for x in current.records:
 for k in current.K:
  opposite=current.MATCH[k];samples=[y["values"][opposite] for y in current.by_team[x["opponent"]] if y["game_id"]!=x["game_id"]]
  opponent=statistics.fmean(samples) if len(samples)>=2 else current.means[opposite][x["opponent"]]
  pool=current.means[opposite]
  opponent_z=(opponent-statistics.fmean(pool.values()))/(statistics.pstdev(list(pool.values())) or 1.)
  adjusted[x["team"]][k].append((x["values"][k]+old_betas[k]*opponent_z,x["plays"]))
units={t:{k:current.wmean(adjusted[t][k]) for k in current.K} for t in current.teams}
component=current.base.standardize({t:statistics.fmean(units[t].values()) for t in current.teams})
rows=[]
for t in current.teams:
 score=.25*component[t]+.35*current.base.competition[t]+.25*current.base.market_strength_with_residual[t]+.15*current.base.results[t]
 rows.append({"team":t,"score_z":round(score,5),"dominance_index":round(50+15*score,2),"four_unit":round(component[t],4),**{k:round(units[t][k],5) for k in current.K}})
rows.sort(key=lambda x:(-x["score_z"],x["team"]))
baseline={x["team"]:x for x in current.new}
for i,x in enumerate(rows,1):
 x["rank"]=i;x["2026_fitted_rank"]=baseline[x["team"]]["rank"];x["rank_change"]=x["2026_fitted_rank"]-i
out={"description":"2026 full available season under 2025 fixed opponent-unit coefficients; same 25/35/25/15 formula and same 2026 inputs otherwise","2025_coefficients":old_betas,"2026_coefficients":current.betas,"teams":len(rows),"team_games":len(current.records),"new_2025_fixed_coefficients":rows,"baseline_2026_fitted_coefficients":current.new,"notes":["Independent new output; does not change the 2026-fitted experiment.","2025 coefficients are frozen from the verified historical archive.","Opposing 2026 unit strengths remain calculated from 2026 completed matchups.","Retrospective descriptive ranks; does not test out-of-sample game prediction."]}
(D/"betwise_2025_coefficients_on_2026_comparison.json").write_text(json.dumps(out,indent=2))
with (D/"betwise_2025_coefficients_on_2026_comparison.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print("2025 fixed coefficients 2026 rankings",[(r["rank"],r["team"],r["2026_fitted_rank"]) for r in rows[:30]])
