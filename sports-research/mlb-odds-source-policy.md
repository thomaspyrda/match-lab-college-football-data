# MLB Historical Run-Line Source and Validation Policy

Updated: 2026-10-19

## Objective
Display a team's pregame standard MLB run-line side (-1.5 if favorite, +1.5 if underdog) on its historical schedule. Color it green if the team's score plus the run line exceeds the opponent's score, red if less, neutral on a push. Never infer favorites from final scores.

## Source candidates, in order
1. Sportsbook Review historical MLB moneyline archive: https://www.sportsbookreview.com/betting-odds/mlb-baseball/
2. Sportsbook Review historical archival data through 2025-08-16: https://github.com/ArnavSaraogi/mlb-odds-scraper (community-maintained, independently validate)
3. Odds Reference 2013–2025: https://oddsreference.com/odds/mlb (cross-check)
4. FastballAPI 2015–2026: https://fastballapi.com/data/mlb-odds-history (requires paid API credentials)
5. Public reference CSV https://github.com/tanhungle/mlb-reference-data/blob/main/odds_flat.csv (supplementary coverage only; provenance must be validated).

Do not use third-party data without checking licensing, access conditions, and data integrity.

## Record linkage
Use local game date, both normalized teams, and game start time/doubleheader number where available. Require unique matching game identity. Check final scores against the already published official MLB game record; do not overwrite official results with odds-source results. Treat postponed, canceled, suspended, and tied/unfinished games according to MLB's official recorded status.

## Decide favorite
Use both teams' **pregame closing moneyline odds from the same sportsbook and timestamp**. The more negative/lower American moneyline is the favorite (e.g. -135 versus +115), regardless of final winner. For multi-book disagreement, choose a fixed named reference book or pre-declared consensus rule and record its provenance. If both teams show equal-priced pick'em, skip side assignment rather than arbitrarily choose. Do not use postgame or live odds.

For each team, store:
- team_runline_side: -1.5 for favorite, +1.5 for underdog
- team_runline_result: W, L, or P from **final official score plus team run line**
- moneyline_source, moneyline_snapshot_time, sportsbook (or explicit consensus provenance)

The opponent's run line must be the opposite side for the same game. Their W/L run-line outcomes must be complementary unless an unusual settlement requires review.

## Calculation
Compare (team runs + team_runline_side) with opponent runs. W if greater; L if lower; P if equal. Standard half-run lines cannot push on completed integer scores.

## Rendering
Schedule columns: Date | Opponent | Score | Result | Run Line | O/U 8.5.
Display only -1.5 or +1.5 in run-line cells; green for W and red for L. Missing unverified side is an em dash; never fall back to universal +1.5. O/U 8.5 is a synthetic fixed comparison, not a verified sportsbook total.

## Operational checkpoints
- Import historical data by season and report total eligible games, uniquely matched games, ambiguous doubleheaders, verified favorites, and unresolved games.
- Validate that all completed matched games assign opposite sides and complementary run-line outcomes.
- Sample-check historical dates against the original odds archive before publishing each season.
- For daily updates, select final pregame odds only and keep official MLB results authoritative.
- Publish a season only if data quality is acceptable; leave individual unresolved games blank, with no invented favorites.

**Status at creation:** Source candidates researched, not yet integrated or independently validated. Historical favorite/underdog records have not been populated by this document.
