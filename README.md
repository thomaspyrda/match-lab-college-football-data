# Match Lab AP + Elo Data Layer

This replaces the attempted full-FBS editorial ranking with two independent pregame signals:

- **AP Top 25**: national recognition and matchup importance. Teams outside the poll are stored as unranked, never as rank 26.
- **CFBD Elo**: performance-based strength for every FBS team. Elo rank is calculated within the FBS field for the same snapshot.

## Timing contract

`effective_week` means the football week whose games may consume the snapshot.

- AP poll week `N` is joined only to games in week `N`.
- Elo requested for week `N` is joined only to games in week `N`. CFBD's weekly Elo endpoint represents the pregame snapshot; this was cross-checked against the game-level `homePregameElo`/`awayPregameElo` fields.
- Week 1 uses the Week 1 poll and CFBD's Week 1 pregame Elo snapshot.
- No postgame result from the target week may enter either value.

## Missing-data contract

- A team absent from a verified AP Top 25 is `is_ap_ranked=false` and `ap_rank=null`.
- Missing Elo remains unavailable. AP status must never fill Elo and Elo must never fill AP status.
- 2026 includes only weeks available as of the build date.

## Raw input layout

The compiler consumes raw API responses beneath `raw/`:

```text
raw/rankings_2015.json
raw/elo_2015_week_1.json
...
```

Rankings responses come from `GET /rankings?year=YYYY&seasonType=regular`.
Elo responses come from `GET /ratings/elo?year=YYYY&seasonType=regular&week=N`, where `N` is the target game's week.

The API key belongs only in the `CFBD_API_KEY` environment variable. It must never be written into a file or browser bundle.

## Outputs

- `match_lab_ap_elo_master.csv`: source-level weekly team rows.
- `match_lab_ap_elo_lookup.json`: compact Hostinger lookup.
- `match_lab_game_ap_elo.csv`: authoritative game-team join rows using exact game-level pregame Elo when supplied.
- `match_lab_game_ap_elo_lookup.json`: preferred Match Lab lookup keyed by CFBD game ID and canonical team.
- `match_lab_ap_elo_coverage.csv`: validation and coverage by season/week.

For historical game comparisons, use the game-ID lookup. `GAME_PREGAME` means the Elo exactly matches CFBD's game record. `WEEKLY_CARRY` is used when CFBD omits Elo on the game record, typically for an FBS-vs-FCS game; the team's verified weekly Elo state is carried without a fabricated change.
