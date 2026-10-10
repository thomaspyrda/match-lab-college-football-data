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
   - Note: CFB Program Accolades NFL first-round draft picks (1970–2026) were previously implemented here, but exact CFB detail renderer and JSON filenames have NOT yet been verified.
2. `thomaspyrda/betwise-nfl-matchup-dashboard` — independent NFL dashboard served at `nfl.parlaycalculator.bet`; branch `main`.
   - Root `index.html`: dashboard markup. Contains existing `game-rail-navigation`, `gamesPrev`, `gamesNext`, and `game-scroll-arrow` elements, reference for NBA arrows.
   - Root `app.js`, `styles.css`: NFL dashboard implementation (file paths referenced in HTML).
   - Root `data/dashboard.json`: dashboard dataset (documented in previous sessions; check presence before editing).
3. `thomaspyrda/betwise-nba-matchup-dashboard` — a separate repository exists, but current `README.md` only identifies it by name and no root `index.html` exists. The functioning NBA Dashboard source has been verified under the CFB Match Lab repo at `nba/dashboard/`. Do not assume this third repository deploys the live dashboard.

## Pending requests (DO NOT mark as implemented)

- CFB team Program Accolades: make every NFL first-round draft pick's receiving NFL team abbreviation link to the correct existing NFL team-page route, including historical franchise aliases. Exact CFB team-detail source path and existing NFL team route mapping must be located before writing.
- NBA Dashboard: add side navigation arrows like the NFL/CFB dashboards. Modify `nba/dashboard/index.html`, `app.js` and `styles.css` only as needed after comparing working NFL implementation.

## Change safety

- Never change site domains or undertake a WiseStats rebrand without explicit user authorization.
- Avoid unrelated layout/data/branding changes.
- First identify active source and deployment route; make targeted edits only, test, and separately confirm whether the change is live.
- Use connected GitHub code access for source edits; the root Hostinger Horizons workspace may not contain the subdomain pages.
