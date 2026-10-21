# Player value data

Basketball-Reference publishes BPM and VORP in its player Advanced tables:
https://www.basketball-reference.com/leagues/NBA_2027_advanced.html
Methodology: https://www.basketball-reference.com/about/bpm2.html

No automated VORP source is connected. ESPN's injury feed supplies availability,
but does not supply the VORP values used here. The dashboard displays missing
values as dashes until a verified current-season export is supplied.

`nba/dashboard/data/player-value.json` is an optional input. It must contain:

- `season`: NBA ending year, e.g. 2027.
- `season_type`: ESPN phase (2 regular season, 3 playoffs).
- `as_of`: source observation cutoff with timezone.
- `source`: HTTPS URL identifying the published data source.
- `coverage`: `league`, with one combined season row per player.
- `players`: rows with verified ESPN `id` (`nba:espn:player:123`), `games`,
  numeric `vorp`, and optional numeric `bpm`.

Map provider player IDs to ESPN IDs explicitly. Do not join ambiguous names.
For traded players, use the provider's combined season total once; do not also
include team-stint rows. The import requires coverage of all players already
observed in the current-season box-score cache. Values more than three days old,
future-dated values, and mismatched seasons/types are rejected.

VORP percentile compares all players with at least one appearance and a verified
VORP value in that season/type. It is 100 × (average ascending rank − 1)/(N − 1).
Ties receive the same average rank; a one-player population has no percentile.
Missing and unplayed players remain blank. This measures accumulated value,
including playing time; it is not a percentage of the team's VORP.

The source access and publication arrangements must be confirmed before wiring
an automatic download. Source data-use information:
https://www.sports-reference.com/data_use.html
