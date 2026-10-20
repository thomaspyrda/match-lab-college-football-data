# MLB historical run-line coverage report

Generated from successful GitHub Actions logs on 2026-10-20. Numbers are unique game identities, not per-team rows.

| Season | Verified games | Official identities | Coverage | Source limitation |
|---|---:|---:|---:|---|
| 2021 | 2,183 | 2,429 | 89.87% | Archive begins March 2021; missing/disputed games |
| 2022 | 2,343 | 2,430 | 96.42% | Missing/disputed games |
| 2023 | 2,381 | 2,430 | 97.98% | Missing/disputed games |
| 2024 | 2,382 | 2,429 | 98.07% | Missing/disputed games |
| 2025 | 1,688 | 2,430 | 69.47% | Archive ends August 16, 2025 |
| **Total** | **10,977** | **12,149** | **90.35%** | 1,172 unresolved identities |

Each verified game has two team records. The source is the public SBR archive at https://github.com/ArnavSaraogi/mlb-odds-scraper/releases/tag/dataset . This is sportsbook odds enrichment; results and scores stay official MLB.

Evidence:
- https://github.com/thomaspyrda/match-lab-college-football-data/actions/runs/39358418106 (2022 and 2023)
- https://github.com/thomaspyrda/match-lab-college-football-data/actions/runs/39358279620 (2024)
- https://github.com/thomaspyrda/match-lab-college-football-data/actions/runs/39358653382 (2021 and 2025)

Important: Match percentage describes agreement of identifiable final-score games with the available historical odds archive. It is NOT independently verified sportsbook closing-line timestamp coverage, nor evidence of live-site deployment.

Open tasks:
1. Verify source timestamp provenance and reconcile ambiguous historical games.
2. Find defensible licensed/free sources for the remaining 2025 games, 2015–2020, and 2026.
3. Independently check live MLB team-page rendering and deployment.
4. Leave missing team_runline_side as em dash; never infer favorite from result.
