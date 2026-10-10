# Sports Website Development Map

Last verified: 2026-10-10. This file is a navigation aid for future ChatGPT development sessions. Documentation only; it does not affect deployed pages.

## GitHub repositories (connected account)

1. `thomaspyrda/match-lab-college-football-data` — CFB Match Lab and cross-sport pages, primary current shared-site source; branch `main`; serves content on `matchlab.parlaycalculator.bet`.
   - Root `index.html`, `app.js`: CFB Match Lab homepage/interface.
   - Root `teams.html`: CFB team directory.
   - `nba/teams/index.html`: NBA team directory.
   - `nba/teams/nfl-style.js`: NBA team-page rendering and archive logic (verified).
   - `nba/dashboard/index.html`: NBA matchup dashboard HTML.
   - `nba/dashboard/app.js`: NBA matchup dashboard interactions, matchup selection and rendering.
   - `nba/dashboard/styles.css`: NBA dashboard styling.
   - `sports-research/team-research.js`: common research presentation/section-order helper; check actual impact before editing.
   - `cfb_program_accolades.py`: verified CFB Program Accolades HTML renderer and NFL draft team links; source data in `data/cfb/program-accolades.json`.
   - `apply_cfb_program_accolades.py`: regenerates accolade sections in all `cfb/teams/<slug>/index.html` pages. Triggered by `.github/workflows/cfb-program-accolades.yml` on changes to the renderer; workflow tests, regenerates, and pushes static team pages.
2. `thomaspyrda/betwise-nfl-matchup-dashboard` — independent NFL dashboard served at `nfl.parlaycalculator.bet`; branch `main`.
   - Root `index.html`: dashboard markup. Contains existing `game-rail-navigation`, `gamesPrev`, `gamesNext`, and `game-scroll-arrow` elements, reference for NBA arrows.
   - Root `app.js`, `styles.css`: NFL dashboard implementation (file paths referenced in HTML).
   - Root `data/dashboard.json`: dashboard dataset (documented in previous sessions; check presence before editing).
3. `thomaspyrda/betwise-nba-matchup-dashboard` — a separate repository exists, but current `README.md` only identifies it by name and no root `index.html` exists. The functioning NBA Dashboard source has been verified under the CFB Match Lab repo at `nba/dashboard/`. Do not assume this third repository deploys the live dashboard.

## Pending requests (DO NOT mark as implemented)

- CFB team Program Accolades: source-code edit completed in `cfb_program_accolades.py` (2026-10-10, commit `28b00069`). Verify workflow generated static pages and live links after deployment.
- NBA Dashboard: navigation arrow code completed in `nba/dashboard/index.html`, `app.js` and `styles.css` (2026-10-10, latest commit `7e758a76`). Verify live deployment and mobile interaction.

## Change safety

- Never change site domains or undertake a WiseStats rebrand without explicit user authorization.
- Avoid unrelated layout/data/branding changes.
- First identify active source and deployment route; make targeted edits only, test, and separately confirm whether the change is live.
- Use connected GitHub code access for source edits; the root Hostinger Horizons workspace may not contain the subdomain pages.
