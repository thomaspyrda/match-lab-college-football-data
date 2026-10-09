# NBA schedules and player statistics

The `*-season-details.json` files cover all 30 NBA teams from 2015–16 through
2025–26. Season keys use the ending year. Only regular-season game IDs beginning
with `002` are imported. Pandemic seasons retain their actual game counts.

Schedules join NBA TeamGameLogs exports from `llimllib/nba_data` to final NBA
BoxScoreTraditionalV3 exports distributed by SportsDataverse. Final box-score
points take precedence over stale archived log scores. The audit records each
correction and its official NBA game URL. Game dates and opponent identities
come from the game logs; home/away designations come from the final box scores.
Bubble games retain the designated side and receive a neutral-site flag.

Player totals are Basketball Reference exports distributed by
`sumitrodatta/nba-alt-awards`, `2026/Data/Player Totals.csv`. Combined `TOT`/`2TM`/
`3TM`/`4TM` rows are excluded. Each team receives only its own player stints.
Per-game values and shooting percentages are derived from those season totals.
Zero-attempt shooting percentages remain null. Six leader categories use team
season totals, with all tied leaders retained. League ranks combine each player's
stints across teams, with ties sharing a rank.

To reproduce or refresh this historical import:

```sh
python -m pip install pandas pyarrow
python nba/pipeline/fetch_season_detail_sources.py --source-dir /tmp/nba-season-sources
python nba/pipeline/import_season_details.py --source-dir /tmp/nba-season-sources
```

The importer validates paired opponents, home/away sides, unique games,
score arithmetic, W/L outcomes, game counts and records against existing team
summaries, team PPG, unique player stints, and equality of each team's summed
player points and season game points. It builds all outputs before saving them.
`season-details-validation.json` records all 330 checks, coverage counts and
SHA-256 hashes of the input files. Updated remote exports may change these hashes.

The shared team renderer displays the first 12 games, followed by a native
expandable section containing the remaining games. The total automatically
reflects the selected team's actual season length. Six NFL-style leader cards
precede a full-roster statistics table. Source links and definitions appear on
the pages. Verified betting data can be merged by game ID or date and opponent;
missing closing lines, ATS and O/U results remain blank.
