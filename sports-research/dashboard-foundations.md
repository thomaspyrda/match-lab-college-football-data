# MLB and CBB dashboards

Both use the NBA/NFL/CFB visual system: select a matchup before seeing details, mirrored team statistics and competition ranks, six form-and-schedule rectangles, full source-reported team rosters, and main logo links to stable team URLs. Date and team search filter the slate. Data refreshes hourly through dedicated GitHub Actions.

## MLB
Current season and phase come from the upcoming slate. Team stats are explicitly requested and validated against ESPN requestedSeason, keeping postseason separate from regular season. Rankings include only teams with a completed sample in that phase. Current totals are labelled snapshots and are not offered as historical pregame data. Probable pitchers are source-reported, not confirmed starters. Recent form uses final games observed in the last eight calendar days, up to five. Run-line and total records exclude unavailable source quotes; closing status is not independently verified. Individual batting and pitching season tables remain a next integration; current roster identity, status, bats/throws and player source links are available.

## CBB
2026–27 profiles use completed box scores from that season type only. Opponent efficiency comes from those box scores. Rankings use all Division I teams with a sample. Estimated possessions and the same observed-before-tipoff restriction as NBA prevent future-result leakage. Before opening day the schedule and rosters are useful, while current-season metrics remain blank and unranked. Roster season checks exclude stale prior-season membership. Division II opponents are currently excluded from the Division I matchup slate. Upcoming roster publication may be incomplete. No prior-season statistics or replacement-value proxies are silently inserted.

## Verification
Five automated source-boundary/rank tests, JavaScript syntax checks, and runtime rendering of every downloaded matchup. Empty states and missing data use dashes, not invented zeros. Browser visual QA was unavailable in this environment.
