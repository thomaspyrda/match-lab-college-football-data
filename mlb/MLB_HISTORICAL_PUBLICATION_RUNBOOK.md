# MLB historical Schedule & Results — controlled release checklist

Scope: 2015–2025 regular-season Schedule & Results for 30 existing MLB team pages. This runbook does not authorize deployment, player-stat publication, or any changes to unrelated sections.

## Required evidence
1. Successful historical staging workflow with all 11 seasons.
2. Official standings reconciliation: 330/330 team-season W/L records matching.
3. Consolidated archive and 30-page nonwriting transform dry-run.
4. Chromium preview checks for season switching, 12-row preview, and full expansion.
5. Review package manifest and SHA-256 source/review checksums.
6. Rollback snapshots independently verified against original SHA-256.
7. Source drift check run against the *actual target branch immediately before applying* files; abort if a file changed.
8. Confirm legal/source terms and desired attribution before publishing game results.

## Release mechanics (not implemented)
- Obtain explicit authorization for the 2015–2025 Schedule & Results release.
- Stage the 30 reviewed pages in a dedicated, human-reviewed pull request rather than directly to main.
- Verify that the 30 changed paths are limited to `mlb/teams/<slug>/index.html`; require zero unrelated diffs.
- Before merge, regenerate review files from the current target branch and compare original SHA-256; do not rely on previously downloaded artifacts as fresh validation.
- Inspect desktop and mobile previews and at least three representative teams, including the 2018 163-game exception and 2020 58-game exception.
- Confirm deployment hosting/source branch and any CDN cache behavior.
- Merge only after required approvals and explicit user instruction.
- After deploy, spot-check season switching and schedule expansion on public URLs, including both normal and exceptional seasons.
- Preserve the exact source revision/rollback artifact and verify restoration instructions before initiating any release.

## Stop conditions
Missing artifacts, failed reconciliation, changed source checksums, unexpected file changes, failed browser test, uncertain licensing/attribution, or missing explicit authorization: **do not publish**.

Current state: reviewed artifacts only; production pages have not been changed.
