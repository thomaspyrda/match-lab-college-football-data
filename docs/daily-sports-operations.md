# Daily sports operations readiness

All five sports have implemented automatic refresh paths and have passed live activation checks. This does not yet prove a complete daily cycle for every newly introduced schedule.

## Completion evidence

| Sport | Latest completion evidence |
| --- | --- |
| CFB | Read-only health 41705938194; deployment 41706036244; subsequent scheduled results and markets also observed successful |
| CBB | Health 41720463318; source and publisher jobs verified; subsequent scheduled results and market capture observed successful |
| NFL | Final health 41746810774; dashboard, independent leaders and team history verified; scheduled market refresh 41757246179 succeeded |
| NBA | Final health 41755778778; independent sources/publications and Pages deployment verified |
| MLB | Final health 41759186773; independent lineup and market collectors and downstream dashboard refreshes verified; successful Pages deployment 41759419967 |

MLB verification reports 2026 postseason, 30 teams, 12 ranked teams, 290 player records, 40 quoted games and no upcoming matchups. The empty offseason slate is intentional.

## Daily checks

The existing per-sport health workflows run on their own schedules. Open the Actions tab in this repository for CFB/CBB/NBA/MLB, and in thomaspyrda/betwise-nfl-matchup-dashboard for NFL. Check the actual scheduled event, successful source collection, downstream publication and final deployment. A push-triggered activation or manually retried job is not evidence of a natural scheduled cycle.

Source files retain their original observations. Do not turn stale inputs into fresh ones by changing timestamps. Failed sources keep previous verified files; missing quotes remain unlined, missing availability stays unknown, and confirmed lineups are never fabricated.

A cancelled overall workflow may contain a successful publisher and a cancelled queued deployment. Inspect individual jobs. Only treat a cancellation as harmless after a later successful deployment contains the relevant public outputs.

## Recovery

1. Inspect the failed step and source validation message before retrying.
2. Retry the failed source or publisher using GitHub Actions, then check its downstream jobs.
3. For a rebase conflict, rebuild from current main; do not automatically choose a conflict side or force-push generated output.
4. Confirm read-only health checks and the final deployment after recovery.
5. Historical backfills remain explicit operations; daily repairs must preserve verified historical seasons.

## Remaining operational acceptance

- Observe one complete natural scheduled cycle after the final source changes for every sport, especially the new MLB jobs. This requires the next scheduled window and cannot be inferred from activation runs.
- Verify the user's GitHub Actions failure-notification preferences. No dedicated external alert destination has been configured or verified in this work.
- Before season rollover, review season arguments/defaults and approved preseason inputs. NFL workflows still contain explicit 2026 defaults; CBB/CFB seed and historical/bootstrap boundaries require deliberate review. Current-season daily readiness does not mean next-season activation is automatic.
- Keep the final successful deployment as the publication acceptance point; queued or superseded deployments alone are not completion evidence.

No UI designs or model formulas were changed by the workflow separation.
