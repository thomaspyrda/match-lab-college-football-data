# CFB team season archives

Run `python build_cfb_team_pages.py` from the repository root. It reads the
unfiltered `data/historical/{year}.json` Match Lab regular-season games, not
the subset of indexable matchup pages. Week 1 and FCS opponents count.

Stable routes: `/cfb/teams/{slug}/`; share a season with `?season=2015`.
Names and current conferences use `data/cfb/team-registry.json`. Each season's
conference comes from its source games. A team's earlier FCS years are not
presented as full FBS seasons. Missing seasons show missing data, never 0–0.

Initial coverage: regular-season results, records, PPG, PPG allowed, home/away/
neutral and conference records, ATS and O/U records, and completed schedules.
The source's regular-season classification includes conference championships;
bowls and postseason are excluded. Scoring ranks compare historical FBS teams
with recorded results, including teams no longer in today's directory.

Lines retain their provider. Closing status and observation timestamps are
unverified, so these lines must not be described as verified closing lines or
used as timestamped pregame market inputs in future matchup tools. Missing
lines are excluded from ATS/O/U records; coverage denominators are displayed.

Leadership appears between Snapshot and Advanced Metrics, matching the NFL
page order. These additional sections clearly show their collection status.
Coaches, full-season advanced metrics, postseason, drafted alumni and six
player leader categories require separate sources before being populated.
Do not repurpose pregame advanced snapshots as final-season statistics.
Future player leaders should use the primary metric before secondary-stat
tiebreakers, matching the NFL implementation.

The SEO builder and dedicated CFB archive workflow rebuild these pages from
committed source data. The dashboard preview publisher also invokes the
archive builder after updating the directory, preserving its team links.
Populated team pages are indexable, have stable canonicals and appear in
`sitemap-cfb-teams.xml`; empty team pages remain noindex.
