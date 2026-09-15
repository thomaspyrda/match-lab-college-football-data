# Match Lab AP Top 25 + Team Strength Data

Public, pregame-safe college-football data for Match Lab covering 2015–2026.

## User-facing metrics

- **AP Top 25** is the official poll position. Unranked teams remain `null`, never No. 26.
- **Team Strength** converts pregame CFBD Elo to a 1–100 score relative to all available FBS teams in the same season and week.
- Raw Elo remains internally for auditability and matching, but Match Lab must display **Team Strength**, never raw Elo or Elo rank.
- **Advanced Team Profiles** contain pregame-only, same-week FBS percentiles for offensive efficiency, defensive efficiency, rushing success, passing success, explosiveness, defensive Havoc, and finishing drives.

## Calculation

`100 × (teams below + (teams tied − 1) / 2) / (available teams − 1)`

The percentile is rounded half-up and clamped to 1–100. Tied Elo values share the midpoint percentile. `top_percent = 101 - strength_score`.

| Score | Tier |
|---:|---|
| 90–100 | Elite |
| 75–89 | Strong |
| 50–74 | Above Average |
| 25–49 | Below Average |
| 1–24 | Weak |

## Production files

Use `match_lab_game_ap_elo_lookup.json` for historical game comparisons and `match_lab_ap_elo_lookup.json` for general team-week or bye-week context. CSV files provide auditable records; `hostinger_lookup.js` is the browser helper.

`data/profiles/{season}.json` contains derived advanced percentile boards. Each effective week is built from CFBD advanced statistics through the previous week only. Completed current-season games are retained in `data/historical/{season}.json` and automatically become eligible comparisons for later games.

The scheduled GitHub workflow refreshes the active season every six hours. Historical advanced profiles are cached after validation, while the current season is rebuilt so newly completed games flow into future pregame snapshots.

Historical matching returns the 10 closest eligible games from Week 2 onward; Week 1 is excluded because teams have no same-season pregame form sample. Each matchup's Season-to-Date Form uses every completed game earlier in that same season—never games played after the compared kickoff.

The private compiler inputs and raw subscription responses are intentionally excluded. Store the CFBD key only in a server-side `CFBD_API_KEY` environment variable.
