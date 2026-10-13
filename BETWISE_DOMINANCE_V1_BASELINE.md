# BetWise Team Dominance Rating v1.0 — PRESERVED RESEARCH BASELINE

Status: retained descriptive research baseline. Not deployed to production. Do not replace, alter, or deploy without explicit authorization.

## Fixed composition
- Four-unit statistical performance (PO, PD, RO, RD): **25%**
- Earned Strength of Competition: **35%**
- Market-implied baseline strength and opponent-weighted ATS: **25%**
- Game results: **15%**

## Frozen unit-specific 2025 coefficients
- Passing Offense relative to opposing Passing Defense: 0.222085
- Passing Defense relative to opposing Passing Offense: 0.274229
- Rushing Offense relative to opposing Rushing Defense: 0.238657
- Rushing Defense relative to opposing Rushing Offense: 0.268369

These are retrospective 2025 season fitted values, not hand-selected 2026 coefficients. The 2026 ratings use the 2026 opponent-unit performance estimates but the above coefficients.

## Primary preserved output
- `data/research/2026/betwise_2025_coefficients_on_2026_comparison.json` — 2026 rankings with frozen 2025 unit coefficients (contains all 136 teams; unchanged 25/35/25/15 composition).
- `data/research/2025/betwise_unit_matched_2025_backtest.json` — complete-season retrospective 2025 replication with the same recipe.
- `data/research/2026/betwise_unit_matched_comparison.json` — 2026-fitted coefficient sensitivity comparison.
- `data/research/2026/betwise_20_45_20_15_vs_25_35_25_15.json` — independent experimental weight sensitivity test only, **not** the accepted baseline.

## Methodology notes
- This is a **descriptive season-to-date dominance ranking**, not a spread prediction model.
- 2025 historical replication covers 762 completed FBS-vs-FBS games with available spreads and 136 FBS teams.
- Available lines are not proven timestamp-verified closing lines.
- Unit strength estimates for retrospective scores use completed-season/season-to-date data, not guaranteed pregame-safe unit values.
- Competition and wins/components may still overlap; preserve that caveat.
- Do not equate retrospective plausibility or rank stability with formally validated accuracy.
- DO NOT change public/live rankings until specifically authorized.
