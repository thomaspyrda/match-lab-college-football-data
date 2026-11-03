# CFB component pipeline

This replaces the combined daily dashboard collector with independent, versioned input producers. Public HTML, CSS, JavaScript, ranking weights, player selection rules, statistical calculations, and page renderers are unchanged.

## Ownership and dependencies

| Component | Workflow | Inputs and publication |
| --- | --- | --- |
| Verified results and schedules | `refresh-cfb-results.yml` | Collects official final scores and fixtures; saves `results.json`. Runs at 04:05 and 16:05 America/New_York. Live scores cannot become final results. Historical seasons use their frozen archives. |
| Dashboard's existing frozen strength inputs | `refresh-cfb-strength.yml` | Runs after verified results. Executes the existing source calculations and V15 promotion; saves `strength.json`. Does not replace the approved public ranking model. |
| Approved public strength rankings | `build-team-strength.yml` | Requires a verified result snapshot no older than eight hours. Replays that current-season result cutoff through the existing collector, then executes the unchanged approved model, validation, and page builders. Retains its weekly schedules and also responds to verified-result completion. |
| Team metrics and play mix | `refresh-cfb-metrics.yml` | Runs after verified results. Reuses the existing raw-statistic calculations and play-mix enrichment; saves `metrics.json`. |
| Player statistics | `refresh-cfb-players.yml` | Runs after verified results. Reuses the existing usage, production, and efficiency calculations; saves `players.json`. Reads the independent injury snapshot without requesting its provider. |
| Coaching and recruiting metadata | `refresh-cfb-metadata.yml` | Runs after verified results; saves `metadata.json`. A metadata outage retains the existing team-page metadata. |
| Live markets | `refresh-cfb-markets.yml` | Independent collector; saves `markets.json`. Runs at 04:00 and 16:00, plus at :07, :27, and :47 from 09:00 through 23:00 America/New_York. Includes postseason team-page markets and explicit upcoming regular-season weeks. |
| Market publication | `cfb-publish-markets.yml` | Overlays only market fields and their observation timestamp on the published dashboard. Does not require result, player, metric, or strength snapshots, or any provider access. A successful provider response without a quote displays an unavailable quote rather than mislabeling a previous quote as current. |
| Weather and venues | `refresh-cfb-context.yml` | Runs after verified results; saves `context.json`. Does not block other collectors or publication. |
| Injuries | Existing `refresh-dashboard-availability.yml` | Remains independently scheduled at 04:35 and 17:05 America/New_York. Missing reports are unknown. |
| Season Leaders | Existing `refresh-fbs-leaders.yml` | Keeps its daily schedule and adds a verified-results completion trigger. Existing final-game and player-box validation remains intact. |
| Team pages | `build-cfb-team-pages.yml` | Assembles current-season schedule, metrics, and leaders offline from component snapshots. Keeps historical seasons, source metadata, and the existing page builder/validator. Refreshes after relevant successful component updates. |
| Full dashboard publication | `cfb-publish-dashboard.yml` | Assembles from saved results, strength, metrics, and player inputs without provider requests. Uses cached venue/forecast information. Reuses the existing dashboard builder, launch validator, schedule/form/location calculations, and data-only publication. |
| Health checks | `verify-cfb-pipeline.yml` | Read-only checks at 06:55 and 18:55 America/New_York compare the verified result cutoff with rankings, leaders, team archives, and dashboard contracts. The manual sport coordinator runs the same checks after its dependent jobs finish. |

## Failure behavior

- A collector commits only its own validated snapshot. An exception, an incomplete final score, a duplicate game ID, or a provider failure caught by the old metric/player collector cannot replace its last good snapshot.
- Verified results are a required prerequisite for new statistical or ranking calculations. Old or wrong-season result snapshots are rejected before modeling. Current-season live scores are cleared until the provider confirms a final score.
- Markets and injury updates continue independently when statistical collectors fail. Markets have their own publication path; they do not wait for full dashboard assembly.
- Dashboard and team-page assembly can reuse the most recent verified current-season statistics and strength data. Collection timestamps remain available in the private component status report. New result publication requires a current result snapshot; it does not relabel missing statistics as freshly collected.
- Initial migration waits for the first required snapshots. The existing published dashboard and team pages remain intact until those inputs are ready.
- All writers of `cfb-dashboard-preview/data/dashboard.json` in this production pipeline share the `cfb-dashboard-data` lock. Every publication uses bounded fetch/rebase/push retries. Same-file conflicts stop publication instead of choosing a side automatically.
- Private input snapshots under `data/cfb/pipeline/` are excluded from the deployed site and from the public ranking producer's staged outputs. The shared filtered deployment workflow owns site publication.

## Preserving existing calculations

The working dashboard source is pinned to commit `ebb7892f2300f67e174e4d57abeb9b18cdf4ee60`. The component runner validates the normalized SHA-256 of that source before executing its original calculation blocks. It does not rewrite their arithmetic. The approved public ranking scripts remain on main and are not modified; only their provider access is wrapped to use the verified result snapshot and independent market observations.

Updating the dashboard's calculation source is deliberate: update the pin and source hash together, and rerun the comparison and offline-publication tests. New-season preseason inputs remain an explicit model setup step, as in the existing system.

`test-cfb-component-pipeline.yml` performs read-only pull-request validation with no provider credentials. It checks calculation equivalence against the existing collector, provider outage isolation, verified-score handling, stale input rejection, market-only publication without statistical snapshots, offline dashboard/team-page assembly, workflow dependency graphs, shared writer locks, and private-input exclusions.

## Activation and verification

1. Merge the pipeline change. The results collector and independent market collector start from their push triggers.
2. Successful results collection starts the dependent collectors, approved rankings, and Season Leaders. Consumers retain the existing published data during initial snapshot creation.
3. Once initial core inputs exist, dashboard and team-page publishers assemble and publish their data. Market publication is independently available from the first verified market snapshot.
4. Check the read-only CFB health report and final Pages deployment. A merged configuration alone does not establish successful end-to-end production verification.

The existing sport coordinator remains a manual end-to-end run. Optional component failures do not prevent assembly from reusing verified prior inputs; the final validation job reports any remaining inconsistencies.
