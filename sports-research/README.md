# BetWise multi-sport team archive

Published routes:

- `/{mlb,nba,cbb}/`: sport research hubs
- `/{sport}/teams/`: searchable directory, always grouped by division or conference
- `/{sport}/teams/{stable-slug}/`: individual team history page
- `?season=2015#history` (MLB) or `?season=2016#history` (basketball): shareable selected season

Run `python build_sport_team_pages.py` to rebuild. The CFB SEO production builder
also calls this builder, so normal refreshes retain and update the sports archive.

## Identity and membership

`data/sports/team-registry.json` contains checked current sport memberships,
provider IDs, logos, aliases and stable URL slugs. The initial snapshot has 30
MLB teams, 30 NBA teams and 365 Division I men's basketball teams in 32
conferences. College conference membership comes from ESPN's **2027** season
group/team endpoints, including transitioning Division I members.

Registry IDs are namespaced (`mlb:espn:15`), not team names. Preserve an existing
team's `slug` when updating its name or affiliation; append new membership
years instead of replacing past years. Current memberships do not establish
historical membership. Past names, relocations and conference changes belong
to the corresponding season/game records, with source evidence.

MLB season keys are calendar years, beginning in 2015. NBA/CBB season keys use
the **ending year**, beginning with key `2016` for 2015–16. This matches ESPN's
season convention. This version creates no invented historical results,
records, metrics, betting lines or conference assignments.

## Add historical data gradually

Create `data/sports/{sport}/teams/{espn_id}.json` for a team when verified data
is ready. The generator automatically loads it into the existing page. Missing
files and missing seasons mean **not collected**, never 0–0, zero statistics,
or a claim that the team did not compete. Use JSON null for unavailable values.

Example shape (illustrative schema, not real game data):

```json
{
  "schema_version": 1,
  "team_id": "mlb:espn:15",
  "seasons": [
    {
      "key": "2015",
      "coverage": "partial",
      "updated_at": "YYYY-MM-DD",
      "team_name": "Name used that season",
      "conference": "Source-confirmed league that season",
      "division": "Source-confirmed division that season",
      "record": null,
      "metrics": {},
      "sources": [{"name": "Provider name", "url": "https://provider.example/season"}],
      "games": [
        {
          "id": "provider:unique-game-id",
          "date": "YYYY-MM-DD",
          "opponent_id": "mlb:provider:opponent-id",
          "opponent_name": "Opponent name at game time",
          "location": "Home",
          "result": "W",
          "score_for": 5,
          "score_against": 3,
          "verified": true,
          "sources": [{"name": "Provider name", "url": "https://provider.example/game"}],
          "market": null,
          "pregame": null
        }
      ]
    }
  ]
}
```

The builder rejects mismatched team IDs, duplicate seasons/game IDs, unverified
games and games/seasons without provenance. `coverage` is `not_loaded`,
`partial` or `complete`; do not label a partial schedule complete. Each sport's
future ingest should validate schedule completeness, cancellations and duplicate
games against its source before marking complete.

The frontend currently renders verified game results and collection status.
Metric summaries, market splits and matchup comparisons can extend this same
record structure later. Do not compute ATS/over-under outcomes unless a sourced
market line is present; preserve bookmaker, timestamp and closing-line status.
Future pregame comparisons must keep observation timestamps, use information
available before the game, and exclude its eventual result from pregame inputs.

## Search indexing

Directories and sport hubs are indexable. Empty individual archives are
`noindex,follow` and excluded from `sitemap-sports.xml`. A team becomes
indexable only after verified results are loaded. Avoid generating thousands
of empty individual season routes: the season selector shares the stable team
page via query parameter. Once a season has substantial verified content,
dedicated season URLs can be added with canonical and redirect rules.
