# Sports pipeline completion

| Sport | State | Evidence / next gate |
| --- | --- | --- |
| CFB | Complete and live | Independent collectors and publishers; 622 verified completed games and 63 upcoming matchups at rollout. Read-only health run 41705938194 and Pages run 41706036244 succeeded. PRs 71 and 72 merged; provider score validation correction deployed. |
| CBB | Complete and live | PR 73 merged; independent collectors and offline public publishers succeeded. Read-only health run 41720463318 and strength publication with Pages deployment in run 41721278325 succeeded. Renderer entry-point correction deployed in 3cdc7794d283caa385a48ca3fb3117d4e967cce3. |
| NFL | In progress | Approved PR 9 merged: statistical and market dashboard writers share a lock and abort unresolved rebase conflicts. Remaining source separation and live verification pending in `thomaspyrda/betwise-nfl-matchup-dashboard`. |
| NBA | Queued after NFL | Separate the remaining bundled daily statistics and publication path in this repository. |
| MLB | Last, offseason priority | Finish remaining separation and verification after the in-season sports. |

Completion refers to the agreed backend workflow separation and reliability scope. Existing UI designs and model formulas remain the baseline. Routine provider corrections and normal operational monitoring continue after completion.
