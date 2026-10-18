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


## Verified offline recheck of original consolidated ZIP
Inspected original artifact `12123510898` directly (not regenerated). Filtering `atBats > 0` yields 7,179 hitters from 7,191 and 0 rank/order violations and 0 intra-team-season duplicate player IDs. By year: 2015–2019=600 each, 2020=582, 2021–2022=600 each, 2023=599, 2024=600, 2025=599, 2026=599. 13 team-seasons now have <20 positive-AB players: 110/2020, 111/2020, 115/2020, 117/2020, 117/2023, 119/2020, 120/2026, 121/2025, 133/2020, 138/2020, 139/2020, 143/2020, 147/2020. This is structural verification only; fresh-source run status is still unconfirmed.
