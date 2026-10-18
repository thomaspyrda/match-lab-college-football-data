# MLB historical player leaders — consolidated QA (2015–2026)

Review source: [GitHub Actions run 39092851946](https://github.com/thomaspyrda/match-lab-college-football-data/actions/runs/39092851946), artifact ID `12123510898` (13 JSON files, 12 annual selections and one combined review).
Review of downloaded JSON performed October 17, 2026 (America/New_York). **Review only. No publication authorized.**

## Verified structural checks
- 30 distinct team IDs and 360 team-seasons, each year 2015–2026 represented.
- 7,191 hitters; 1,800 starting pitchers; 1,800 relief pitchers = 10,791 selected player-stat records.
- For every team-season: hitters sorted descending on `stats.atBats` and no more than 20; exactly five starters and five relievers; no duplicate pitcher IDs between the selected pitcher groups; all records have `attribution=explicit_team_split`.
- Selection implementation `select_mlb_player_leaders.py`: hitter rank by descending team-season at-bats (player ID used solely as exact-AB tiebreaker); starters by starts, then appearances; relievers by relief appearances (games played minus games started), excluding selected starters.

## Exceptions requiring source-coverage inspection
2020 hitter counts below 20:
| MLB team ID | Hitter count | Shortfall |
|---|---:|---:|
| 115 | 17 | 3 |
| 117 | 17 | 3 |
| 119 | 19 | 1 |
| 133 | 19 | 1 |
| 139 | 19 | 1 |

The nine-record shortfall is **not proof of missing leaders**, because some teams may have had fewer than 20 eligible players in the source. Compare these five team-season source player lists independently before concluding.

Additional observations:
- 12 selected hitters have zero team-season at-bats; this can occur at the bottom of a short eligible list and requires review of source coverage/eligibility, not automatic deletion.
- 263 selected relief-pitcher rows have at least one game started; this is not by itself a defect. The selection algorithm ranks by relief appearances, and excludes five selected starters per team.


## Follow-up: 2020 shortfall cross-checked with published batting totals
**Independent 2020 team-total reconciliation (all five exceptions passed):**

| Team ID | Team | Selected hitters | Staged AB | Published AB | Staged H | Published H | Staged HR | Published HR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 115 | Colorado Rockies | 17 | 2057 | 2057 | 528 | 528 | 63 | 63 |
| 117 | Houston Astros | 17 | 1992 | 1992 | 478 | 478 | 69 | 69 |
| 119 | Los Angeles Dodgers | 19 | 2042 | 2042 | 523 | 523 | 118 | 118 |
| 133 | Oakland Athletics | 19 | 1908 | 1908 | 430 | 430 | 71 | 71 |
| 139 | Tampa Bay Rays | 19 | 1975 | 1975 | 470 | 470 | 80 | 80 |

Published source references:
- [Baseball-Reference MLB 2020 standard batting, complete team totals](https://www.baseball-reference.com/leagues/majors/2020-standard-batting.shtml)
- [MLB.com 2020 team batting](https://www.mlb.com/stats/team/2020)
- [Baseball-Reference Oakland 2020](https://www.baseball-reference.com/teams/OAK/2020.shtml)

The aggregate AB, H, and HR sums of all staged hitters match published regular-season **team totals** for each exception. This is strong independent evidence that the <20 count for these teams is legitimate under the source's hitter eligibility convention. This **does not** independently prove each player identity or per-player figure, and does not validate the remaining team-seasons or pitchers.

Important distinction: the 2020 shortfall can now be considered reconciled on these three cumulative batting statistics; the global independent leader coverage gate remains open.

## Important limitation
The checks establish only internal consistency **of the retrieved records**. They do **not** establish that every actual top-20-by-at-bats hitter was present in the underlying source data. The review JSON itself says independent source-coverage audit is required. Also `full_roster_reconciled=False` in selection code.

## Next gate (before any team-page integration)
1. Independently compare a sample of selected hitters against authoritative MLB team-season batting leader lists, and examine the five 2020 exceptions.
2. Confirm pitcher selections and key displayed statistics from source splits.
3. Create a mapping + non-writing transform preview against the existing team-page structures.
4. Preserve no-publication guards, run page/season switching preview checks, and obtain explicit authorization before any public change.

**Publication state: blocked pending independent source-coverage evidence.**

## Targeted validation implementation
A new read-only script at `audit_mlb_historical_leader_coverage.py` independently re-queries the **same MLB Stats API** with the alternate no-playerPool endpoint and checks staged leader identity/order and per-player AB/H/HR. Its use must not be misrepresented as independent third-party verification. It is intentionally scoped by explicit `--years` and `--team-ids` options to avoid excessive source queries.

Suggested first pass: `--years 2019,2020,2025,2026 --team-ids 115,117,119,133,139,147` (24 team-seasons). The archive input must be the downloaded consolidated artifact JSON. This command is **not yet executed**; no pass counts have been claimed. Continue only after inspecting discrepancies, and keep all deployment/publishing controls disabled.

## Execution blocker and explicit next action
The GitHub connector available in this review does not provide a workflow-dispatch action, and no completed fresh-source comparison artifact has been retrieved. To run the existing sample audit in GitHub, open **Actions → Audit MLB Historical Hitter Coverage (Review Only) → Run workflow**, select branch `audit/mlb-player-historical-2015-2026`, and run it. Then inspect/download the `mlb-hitter-coverage-sample-audit-no-publication` artifact. Do not mark source completeness passed until its JSON reports 24 checks, 24 passed, 0 failed and 0 execution errors. No publication is authorized.
