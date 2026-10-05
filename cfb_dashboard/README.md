# BetWise CFB Dashboard

Development foundation for a college-football matchup dashboard modeled on the BetWise NFL Dashboard while preserving Match Lab's pregame-safe data rules.

## Scope

- FBS matchup dashboard
- 2015-2026 historical foundation
- pregame-safe season-to-date profiles
- V15 Team / Offensive / Defensive Strength integration
- SOS and AP rank context
- offense-vs-defense matchup metrics
- form and schedule context
- market, venue and weather fields
- featured mismatch and trend-ready output
- player layer reserved for a later cross-sport phase

## Safety rule

A profile for season Y / week W may only use completed games with week < W. End-of-season statistics must never leak into earlier historical matchups.

## Browser contract

The future frontend reads generated JSON. It does not call CFBD directly and never contains an API key.

See `schema/dashboard.schema.json` for the initial contract.
