# MLB positive-at-bats hitter eligibility review — no publication

The consolidated artifact 12123510898 was inspected directly. The current staged archive contains 7,191 selected hitter rows, including **12 with atBats=0** (2020: 9, 2023: 1, 2025: 1, 2026: 1). These entries include pitchers and one outfield specialist; none contributed an actual hit opportunity counted as an at-bat for that team-season.

## Review-only change
The hitter selection code on this audit branch now requires `atBats > 0` before ranking by descending team-specific at-bats, preserving the original tie-break rule. The fresh-source comparator was updated to apply the same eligibility definition.

The **archived** selection JSON has not been overwritten or regenerated, and is still the original 7,191-hitter data. If the same archived selections are merely filtered for display, projected totals would be:

| Year | Positive-AB hitters |
|---|---:|
| 2015–2019, 2021–2022, 2024 | 600 each |
| 2020 | 582 |
| 2023 | 599 |
| 2025 | 599 |
| 2026 | 599 |
| **Total** | **7,179** |

The 12 removed rows affect nine team-seasons. A regenerated upstream source could conceivably contain other positive-AB candidates for some teams: **do not infer the counts above are final top-20-complete selections** until source coverage is independently confirmed.

## Pending
- Existing 24 team-season fresh-source comparison run has not produced a verified result.
- The comparator currently accepts the old staged archive and will flag zero-AB rows as discrepancies in affected samples: rerun the selection with the corrected rule to obtain meaningful end-to-end verification; preserve the original artifact as an immutable baseline.
- No live MLB team pages or default branch files changed.
