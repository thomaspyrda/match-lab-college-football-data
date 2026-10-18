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

## Important limitation
The checks establish only internal consistency **of the retrieved records**. They do **not** establish that every actual top-20-by-at-bats hitter was present in the underlying source data. The review JSON itself says independent source-coverage audit is required. Also `full_roster_reconciled=False` in selection code.

## Next gate (before any team-page integration)
1. Independently compare a sample of selected hitters against authoritative MLB team-season batting leader lists, and examine the five 2020 exceptions.
2. Confirm pitcher selections and key displayed statistics from source splits.
3. Create a mapping + non-writing transform preview against the existing team-page structures.
4. Preserve no-publication guards, run page/season switching preview checks, and obtain explicit authorization before any public change.

**Publication state: blocked pending independent source-coverage evidence.**
