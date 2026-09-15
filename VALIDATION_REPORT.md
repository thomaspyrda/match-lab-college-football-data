# Validation Report

## Advanced pregame profiles

- Seven advanced categories are converted to 1–100 same-season, same-week FBS percentiles with midpoint handling for ties.
- Each effective week uses CFBD data only through `effective_week - 1`.
- Defensive efficiency is direction-adjusted so higher percentiles always mean stronger performance.
- Current-season completed games become eligible historical matches only after a final result exists.
- Season-to-Date Form includes every completed game earlier in the same season and excludes later games.
- Each search displays the 10 closest eligible historical matches.
- Historical candidates require at least one completed prior game and a usable advanced pregame profile for both teams. This excludes Week 1 and delayed openers without relying on the schedule's week label.
- Every available FBS profile exposes its same-week Strength Rank and Team Strength score/tier in the interface.
- Spread, moneyline, and total selections render distinct pregame factor snapshots while percentile rows retain a consistent neutral presentation.
- Raw CFBD subscription responses and `CFBD_API_KEY` are never written to the repository.

- Seasons: 2015–2026
- AP/Elo snapshots: 170
- Weekly FBS team rows: 22,246
- Game-team rows: 17,199
- Direct CFBD game-level pregame Elo rows: 16,530
- Direct pregame Elo mismatches: 0
- Verified weekly Elo carry rows: 669
- Game rows with Elo unavailable: 0
- Duplicate game/team keys: 0
- AP board coverage: 170 of 170 snapshots valid, including official ties
- Full weekly Elo coverage: 155 snapshots
- Team Strength availability parity with Elo: PASS
- Team Strength range, tier boundaries, tied-Elo midpoint handling, JSON/CSV parity: PASS
- 2020 inactive-team exception: 15 snapshots omit New Mexico State; no value was fabricated.
- 2026 scope: Weeks 1–2, matching availability on September 11, 2026.
- Credential and raw-response exclusion: PASS

Raw Elo is retained internally. The website must display Team Strength.
