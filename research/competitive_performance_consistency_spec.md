# Competitive Performance Consistency (CPC) — research specification

Status: RESEARCH-ONLY. Do not connect to published team rankings without out-of-sample validation.

## Purpose
Separate demonstrated performance against strong opponents from a record accumulated against weak opponents. Complement the existing pregame opponent-adjusted efficiency and MOV evidence without double counting.

## Pregame inputs and no-leakage guarantee
For every game g, freeze opponent offensive, defensive and overall strength from only games completed before kickoff plus the approved preseason prior. Never label a past opponent using its final-season ranking. Rank tiers are descriptive only:
- 1–25 elite/high level
- 26–50 strong
- 51–70 intermediate
- 71+ weaker
Actual scoring function must vary continuously with strength; no discrete tier cliffs.
No market spread, result, stat or opponent rating updated after kickoff may influence the historical pregame expectation for that game.

## Four separate reporting dimensions
1. High-level exposure: games played against frozen pregame top-25/top-50 (diagnostic, not independently rewarded).
2. Quality results: actual win/draw/loss against pregame win probability, with opponent quality reflected in expectation; cap per-game result surprise.
3. Competitive performance: margin and underlying opponent-adjusted offense/defense versus pregame expectations for ALL games, including losses.
4. Consistency and weak-opponent accountability: robust dispersion of game-level expectation residuals, with explicit downside checks for weak opposition.

## Required weak-opponent behavior validation
- A win alone cannot imply positive credit: if actual performance is below expected, it creates negative evidence.
- Against weaker opponents, expected statistical and scoring performance is higher; dominance that merely meets that expectation is neutral.
- Positive residuals for extremely weak/FCS opponents remain limited by the explicit existing FCS asymmetric policy; negatives can still penalize.
- Do not impose an additional independent weak-opponent penalty on an already strength-adjusted spread residual without demonstrating improvement.
- A 3-point underperformance against weaker and stronger opponents is scored equally *relative to their respective expectation* unless an additional asymmetry is empirically justified.
- Equivalent positive/negative deviations should be symmetric before any documented ceiling.
- A team without strong-opponent results has less demonstrated evidence of elite-level ability than a team repeatedly performing strongly against elite teams. Apply a modest, reliability-aware evidence discount or ceiling for low-quality schedules, even if weak-opponent results are dominant. Do not label unplayed games as losses; lower confidence/proven-quality credit instead. Do not reward a tough schedule alone: poor performance against elite teams still counts negatively.
- A 4–1 record against strong opposition matters through repeated positive result and performance surprises; wins already rewarded elsewhere must not be counted again at full weight.

## Reliability and aggregation
Aggregate game evidence after computing per-game residuals. Use sample-size shrinkage, leave-one-game-out sensitivity and explicit coverage indicators. Do not use a simple raw sum or assign advantages just for more games. Track performance by opponent tier only for explanation.

## Research arms
A. Frozen-pregame existing baseline
B. Existing 10% separate market-MOV component
C. Baseline plus continuous CPC (initial 5%, carved out of baseline weight)
D. 10% MOV plus CPC as a carefully calibrated *non-redundant* diagnostic, not automatic additive bonuses

## Acceptance tests
- Strict walk-forward holdout by game date and weeks, and historical seasons when source data are available.
- Predict future winner and scoring margin, plus spread residual on held-out games.
- Verify game-level signs and ordering for weak opponents; report FCS handling.
- Report calibration by opponent-strength bins, coverage and number of high-level games.
- Report correlation of CPC with scoring, MOV, QRR, CSC; reject redundant variants.
- Audit New Mexico, SMU, Oklahoma, Texas, Miami, Navy and Rutgers; include leave-one-out ranks.
- Never tune weights simply to make AP-like rankings or to force named teams to move.

No production changes are authorized by this document.

## Revised requirement (October 11 2026)
Strong-opponent results should carry greater proven-quality credit than identical statistical overperformance against weak opponents, provided the adjustment is driven by actual results. Repeated weak-schedule blowouts may indicate underlying talent but provide limited *proven* elite strength. Model this as bounded, continuous evidence quality, not a purely schedule-based arbitrary punishment. A team with no strong opponents can have a high statistical projection yet a lower proven-quality rating.
