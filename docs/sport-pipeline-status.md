# Sports pipeline completion

| Sport | State | Evidence / next gate |
| --- | --- | --- |
| CFB | Complete and live | Independent collectors and publishers; 622 verified completed games and 63 upcoming matchups at rollout. Read-only health run 41705938194 and Pages run 41706036244 succeeded. PRs 71 and 72 merged; provider score validation correction deployed. |
| CBB | Implementation prepared; live verification pending | Separate results, boxes, players, metrics, rosters and markets; offline public publishers. Must pass CI, live activation, freshness verification and Pages deployment. |
| NFL | Queued after CBB | Audit and separate remaining collectors/publication in `thomaspyrda/betwise-nfl-matchup-dashboard`. |
| NBA | Queued after NFL | Separate the remaining bundled daily statistics and publication path in this repository. |
| MLB | Last, offseason priority | Finish remaining separation and verification after the in-season sports. |

Completion refers to the agreed backend workflow separation and reliability scope. Existing UI designs and model formulas remain the baseline. Routine provider corrections and normal operational monitoring continue after completion.
