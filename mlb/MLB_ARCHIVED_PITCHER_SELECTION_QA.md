# MLB archived pitcher selection — structural QA

Artifact: consolidated GitHub Actions artifact 12123510898, 2015–2026. Inspected original ZIP without re-querying MLB data. **Review only; not source-completeness validation.**

| Check across 360 team-seasons | Finding |
| --- | --- |
| Selected starters sorted by descending `gamesStarted`, then descending `gamesPlayed`, then player ID | 0 violations |
| Selected relievers sorted by descending `gamesPlayed - gamesStarted`, then player ID | 0 violations |
| Selected starters with zero starts | 0 |
| Selected relievers with zero relief appearances | 0 |
| Pitcher entries with gamesStarted greater than gamesPlayed | 0 |
| Duplicate hitter IDs within team-season | 0 |
| Zero-AB hitter rows in immutable source archive | 12 |

This verifies internally consistent sorting **among retrieved selected records**, not that the underlying source included all higher-ranked pitchers or hitters. The fresh-source verification workflow has no confirmed completed result, and `fetch_commit_workflow_runs` only provides PR-triggered runs; an empty result cannot be interpreted as definitive proof a push workflow did not run.

No production pages, default-branch files, or deployment settings were altered. Publication remains disabled.
