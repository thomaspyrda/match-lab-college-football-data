# Historical MLB player archive — offline integrity addendum

Scope: existing GitHub Actions consolidated review artifact `12123510898`, with 2015–2026 records for 30 teams. No live source/API re-query was performed for this addendum.

## Offline check from downloaded JSON
- All 360 team-season entries are present.
- Yearly counts: 2015–2019 and 2021–2026 each have 600 hitters, 150 selected starters, 150 selected relievers. The shortened 2020 season has 591 hitters, 150 selected starters, 150 selected relievers.
- The hitter selection groups contain **zero duplicate player IDs within the same team-season**.
- All selected pitcher rows include both `gamesStarted` and `gamesPlayed`.
- **12 selected hitter entries have 0 season at-bats**: 2020 (9); 2023 (1); 2025 (1); 2026 (1). This is consistent with the source including pitching-only appearances among hitting records and does not itself prove a missing higher-AB player. It does raise a user-facing eligibility question (zero-AB entries may be undesirable on hitter cards).

## Actionable verification caveats
The targeted fresh-source verification workflow has been committed at `.github/workflows/audit-mlb-historical-hitters.yml` to the audit branch. A completed GitHub Actions run and any fresh MLB Stats API comparison results **have not been verified** yet. Do not mark the 24-team-season source check as passed.

The comparison uses a second query to the **same** official MLB Stats API, so full independently sourced validation remains outstanding.

2020 missing-20 slots were previously reconciled against team totals in the earlier review, but do not extend that conclusion to unrelated team-seasons.

## Publication controls
This is a research-only draft PR. No content on `main`, live MLB pages, or deployment settings has been changed. Publishing requires a separately approved release and fresh source-coverage verification.
