# BetWise five-sport team page data coverage contract

Updated: 2026-10-08

## Canonical display order
1. Season Snapshot
2. Leadership / Coaches
3. Schedule & Results
4. Advanced Team Metrics
5. Player Statistics
6. Franchise Accolades

A single selected season must control sections 1–4. Franchise accolades are all-time and are not filtered to the selected year. NFL, CFB, MLB, NBA and CBB must have identical heading hierarchy, select placement, tabs, mobile navigation, spacing, color handling, and incomplete-data messages. Each sport has its own statistical columns.

## NBA historical archive
- Target seasons: 2015–16 to 2025–26 complete; 2026–27 regular-season progress as games conclude.
- Official regular-season game logs: NBA Stats via nba_api. **Pipeline exists; published historical output not yet verified.**
- Team rating calculations: explicitly labeled *estimated from box scores*, not falsely presented as official NBA advanced ratings.
- Player chart: nba_api LeagueDashPlayerStats, regular-season averages only; no preseason substitution.
- Awards: NBA Finals champions, conference winners, MVP, All-NBA First Team, DPOY, ROY, Sixth Man, MIP, Finals MVP and Coach of the Year. Need source-level records, recipient, award season, franchise identity, and verification.
- Awards coverage extends before 2015; franchise relocations and name changes require explicit franchise continuity mapping.

## Separate data dependencies
- Schedules, results, box scores and derived team statistics: public league data where legally and technically available.
- Historical closing spreads, totals, ATS, O/U and opener-to-close movement: **not supported by game box-score feeds**; needs a trustworthy historical odds source with permitted reuse.
- Game-by-game injuries/inactives: season-appropriate dated status source required.
- Historical coaches and franchise achievements: official league/team or other attributed, validated registry.

## Quality gates before declaring done
- Page present for every team; selection works for every included year.
- Actual regular-season source rows and summary agree; no fabricated values.
- No double-counting playoffs or preseason; samples explicitly labeled.
- Missing market records stay unavailable, not counted as losses or pushes.
- Mobile and desktop render verification on representative teams across all five sports.
- GitHub commit **is not evidence** of live deployment; confirm published pages independently.

## Leadership role rules
- NBA: Head Coach only.
- CBB: Head Coach only.
- MLB: Manager and Pitching Coach only.
- NFL and CFB: retain Head Coach, Offensive Coordinator, and Defensive Coordinator per existing football design.
- Staff assignments must reflect the selected season, not automatically carry current coaches into previous seasons. Missing records remain unverified.
