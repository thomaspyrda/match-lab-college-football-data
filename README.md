# Match Lab AP Top 25 + Team Strength Data

Public, pregame-safe college-football data for Match Lab covering 2015–2026.

## User-facing metrics

- **AP Top 25** is the official poll position. Unranked teams remain `null`, never No. 26.
- **Team Strength** converts pregame CFBD Elo to a 1–100 score relative to all available FBS teams in the same season and week.
- Raw Elo remains internally for auditability and matching, but Match Lab must display **Team Strength**, never raw Elo or Elo rank.

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

The private compiler inputs and raw subscription responses are intentionally excluded. Store the CFBD key only in a server-side `CFBD_API_KEY` environment variable.
