# CFB team season archives

Run `python build_cfb_team_pages.py` from the repository root. It reads the
unfiltered `data/historical/{year}.json` Match Lab regular-season games, not
the subset of indexable matchup pages. Week 1 and FCS opponents count.

Stable routes: `/cfb/teams/{slug}/`; share a season with `?season=2015`.
Names and current conferences use `data/cfb/team-registry.json`. Each season's
conference comes from its source games. A team's earlier FCS years are not
presented as full FBS seasons. Missing seasons show missing data, never 0–0.

Coverage: regular-season results, records, PPG, PPG allowed, home/away/
neutral and conference records, ATS and O/U records, leadership, incoming
recruiting class rank, paired season metrics, six full-season player leaders,
season outcome and a schedule including postseason and upcoming games.
The source's regular-season classification includes conference championships;
the snapshot excludes bowls and postseason. Scoring ranks compare historical FBS teams
with recorded results, including teams no longer in today's directory.

Lines retain their provider. Closing status and observation timestamps are
unverified, so these lines must not be described as verified closing lines or
used as timestamped pregame market inputs in future matchup tools. Missing
lines are excluded from ATS/O/U records; coverage denominators are displayed.

Leadership appears after Snapshot, with Recruiting Class directly below it,
followed by Advanced Metrics, Season Leaders and Schedule. Season Result
appears within Snapshot, matching the NFL page order. Head coaches are source
records; the provider does not supply historical coordinator roles. Recruiting
rank describes the incoming signing class, not portal or current-roster rank.
Season and player totals include postseason where supplied by CFBD; advanced
metrics exclude garbage time. Never use pregame snapshots as season totals.
Player leaders use the category metric before secondary-stat tiebreakers;
league ranks still share ties on the category total. QB rating uses the NCAA
formula. Missing individual statistics are shown as dashes.

Run `python refresh_cfb_team_details.py` with the existing `CFBD_API_KEY`
environment secret. Cache historical details and refresh the current year.
Run `python supplement_cfb_2015_defense.py` to fill the primary provider's
2015 defensive-stat gap from ESPN cumulative season leaders and player
statistics. ESPN type 3 already includes the regular season, so it must never
be added to type 2. Bowl teams use type 3; other teams use type 2. The
supplement is cached and carries provenance.

The SEO builder and dedicated CFB archive workflow rebuild these pages from
committed source data. The dashboard preview publisher also invokes the
archive builder after updating the directory, preserving its team links.
Populated team pages are indexable, have stable canonicals and appear in
`sitemap-cfb-teams.xml`; empty team pages remain noindex.
