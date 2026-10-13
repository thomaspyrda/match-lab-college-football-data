#!/usr/bin/env python3
"""Research-only weight sensitivity: historical 2025 betas held fixed, 2026 data unchanged."""
import csv,json
from pathlib import Path
import test_betwise_2025_coefficients_on_2026 as prior
D=Path("data/research/2026")
old=prior.rows
old_by={r["team"]:r for r in old}
base=prior.current.base
weights={"four_unit":.20,"earned_competition":.45,"market_strength_ats":.20,"results":.15}
new=[]
for r in old:
 t=r["team"]
 components={"four_unit":r["four_unit"],"earned_competition":base.competition[t],
             "market_strength_ats":base.market_strength_with_residual[t],"results":base.results[t]}
 score=sum(weights[k]*components[k] for k in weights)
 new.append({"team":t,"score_z":round(score,5),"dominance_index":round(50+15*score,2),
             "previous_rank":r["rank"],"previous_rating":r["dominance_index"],
             **{k:round(v,5) for k,v in components.items()}})
new.sort(key=lambda r:(-r["score_z"],r["team"]))
for i,r in enumerate(new,1):
 r["rank"]=i
 r["rank_change"]=r["previous_rank"]-i
out={"season":2026,"description":"Change only overall weight distribution, holding frozen 2025 opponent-unit coefficients, 2026 inputs and component methods fixed",
"new_weights":weights,"previous_weights":{"four_unit":.25,"earned_competition":.35,"market_strength_ats":.25,"results":.15},
"unit_coefficients_source":"2025 fitted, held fixed","unit_coefficients":prior.old_betas,
"model_caveats":["Both variants are descriptive retrospective rankings, not forecasts.",
"Competition credit is still the existing weighted win-loss credit, not a revised opponent-quality/performance formula.",
"Four-unit component reused from the previous rounded export; small rounding differences are possible.",
"Prior experiment files are preserved."],
"new_20_45_20_15":new,"previous_25_35_25_15":old}
(D/"betwise_20_45_20_15_vs_25_35_25_15.json").write_text(json.dumps(out,indent=2))
with (D/"betwise_20_45_20_15_vs_25_35_25_15.csv").open("w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(new[0]));w.writeheader();w.writerows(new)
print("20/45/20/15 top 30",[(x["rank"],x["team"],x["previous_rank"]) for x in new[:30]])
