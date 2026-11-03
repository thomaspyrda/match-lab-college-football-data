# CBB independent component pipeline

Daily CBB schedules and verified results no longer request team statistics, player statistics, rosters, coaches or markets. Each source writes its own season-scoped snapshot under `data/cbb/pipeline/`. Publishers project those saved facts into the existing archive and dashboard contracts using the existing calculation and rendering functions.

| Source | Publication | Failure behavior |
| --- | --- | --- |
| Verified schedules/results | Team schedules, records, upcoming matchups | Keep verified team schedules on a failed team request; refuse an empty response that would erase known games |
| Verified team boxes | Dashboard statistics and strength inputs | Require agreement with final scores; quarantine incomplete or conflicting boxes and retry |
| Player facts | Team players, dashboard player summaries, current leaders | Retry missing player boxes independently; retain verified facts; season fallback requires matching verified point totals |
| Team metrics | Historical metric ranks and strength page columns | Use complete verified boxes or matching games-played/point-total season statistics |
| Rosters and coaches | Dashboard roster and team coach fields | Retry unavailable observations and keep the previous observation |
| Pregame markets | Live dashboard markets | Publish independently of statistical inputs; use pretipoff or trusted archived quotes for historical grading |

`cbb-team-archives.yml` remains the existing scheduled entry point, now collecting results only. Its explicit historical-backfill input and bootstrap import route delegate to `cbb-historical-archives.yml`; daily work does not rewrite frozen history. Public publishers keep the established HTML renderers, dashboard schema, formulas, rankings, coefficients, leader thresholds and model weights.

Per-component locks serialize each source. Publishers stage only their own output files, rebase onto the latest main branch, and retry rejected pushes without resolving conflicts automatically. Dashboard statistics and market publication share one writer lock. Team publication and historical backfills share another.

Public publishers invoke the reusable Pages deployment explicitly, because a results → boxes → metrics/players → publisher chain reaches GitHub's three-level workflow-run limit. This ensures the latest validated public output reaches Pages. Internal snapshots are excluded from the Pages artifact. Existing CFB and other sport publication paths remain in place.

Validation: `python -m unittest discover -s tests -p 'test_cbb*.py' -v` checks source isolation, verified score handling, delayed inputs, exact existing aggregation behavior, market timing, stale strength inputs and fully offline dashboard assembly. `python scripts/check_cbb_workflows.py` checks reusable calls, triggers, writer locks and deployment wiring. `python scripts/verify_cbb_pipeline.py` is read-only and checks live publication provenance and freshness; pending sources are reported separately. The existing sport dataset contract check also remains enabled.

Completion requires successful live source jobs, all public publications, the read-only health check and Pages deployment. Passing local tests or merging this change alone does not mark CBB complete.
