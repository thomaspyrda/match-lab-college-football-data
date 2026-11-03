# Sport data pipeline: safe phased migration

## Non-negotiable preservation rules
Do not change the established CFB/CBB/NFL/NBA/MLB rankings formulas, model weights, player-stat calculations, historical season data, page templates, CSS, hero artwork, advertising or navigation as part of orchestration.
Workflow coordination and publishing should change independently of visuals or calculations.

## Phase 1 implemented
- Existing daily schedules remain active until replacements are manually verified; no cutover yet.
- New manual-only sport coordinators invoke original, reusable production workflows.
- CBB: team results/archive collection precedes dashboard and strength ranking recalculation; markets run independently.
- NFL: validated dashboard/strength precedes team history and season leaders; injury and markets run independently.
- CFB: schedule collection precedes team-strength and season-leader refreshes.
- NBA and MLB currently have combined build stages; separating collection/metrics/publication is still required.
- Five independent injury jobs now update separate per-sport JSON outputs without touching rankings.

## Dependency contract
1. Verified final scores and game IDs before derived team metrics.
2. Verified player boxes before player metrics and season leaderboards.
3. Required complete team metric input before refreshed team strength rankings.
4. Compatible versioned datasets before dashboard and Match Lab outputs.
5. Independently collected injury and pregame market data must not block results or rankings.
6. Last known good snapshot stays published when required data is missing. Never silently label incomplete rankings as current.
7. Public page validation must verify game-through date and results, not just GitHub Actions success.

## Output ownership contract
- NFL dashboard and team ranking production: NFL repository data/dashboard.json and data/nfl-rankings.json.
- NFL team archives: data/team-history/; NFL leaders: data/season-leaders/.
- CBB team archive owner: data/cbb/teams/ and cbb/teams/.
- CBB strength owner: data/cbb/strength-* and cbb/rankings/.
- CBB markets owner: data/cbb/markets/ and data/cbb/pregame-markets/.
- Player availability owner: data/dashboard-availability/<sport>.json, one independent job per sport.
- NBA, MLB and remaining CBB outputs must be assigned exclusive writers before splitting legacy jobs.

## Required cutover tests
- Manually run coordinators on completed game dates and verify all expected game IDs on public team pages and rankings.
- Verify no-change reruns; verify delayed game/partial box does not block unrelated valid results.
- Compare formulas and rendered page templates before/after; retain frozen historical outputs unchanged.
- Verify competing workflow writers are removed or serialized before enabling scheduled coordination.
- Switch one sport at a time. Keep existing production schedule until newly coordinated run is verified.

At this stage the new coordinators are opt-in/manual only. They are not claimed to be fully migrated production schedules.
