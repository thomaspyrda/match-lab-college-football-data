# Morning publication

NFL, CFB, NBA and CBB target completion before 05:00 America/New_York.
MLB is excluded from the new coordinator schedules.

- 02:30: ordered results -> boxes -> metrics/players -> rankings and publication.
- 03:15: repeat to collect late provider data.
- 04:00: repeat and publish verified inputs.
- 04:30: independent workflow checks morning source timestamps and live public JSON;
  requests recovery when incomplete and no coordinator is active.
- 04:40: final scheduled recovery pass; it may complete after 05:00 if data or runners are delayed.

Existing afternoon refreshes and later catch-up schedules remain available. The
coordinators reuse existing builders and formulas. Pending sources fail the audit
even when a collector exits successfully. No pending values are fabricated.
The public audit compares JSON for dashboards, rankings, leader datasets, CFB
current-season details, NBA current-season team data, and all CBB team archives.

## Independent recovery clock

GitHub schedules are best effort. A separate ChatGPT task can inspect the
coordinators at 02:40 and 04:40 Eastern. If no current run is active and collection
or publication is missing, it can re-run the job named Morning recovery entry
point through the connected GitHub app. GitHub re-runs that job and its dependent
jobs, and every collector checks out current main-branch data. The selected
coordinator must include all active sports (schedule, repository_dispatch, or
push event) and be less than 30 days old; do not replay a one-sport manual run
as recovery for all sports. Check run_started_at/run_attempt and job start times,
not just created_at, when recognizing a recovered morning run.

The task is a second scheduler, not a guaranteed execution SLA. Its installation
and first execution must be confirmed separately. For an infrastructure-only
backup, configure a separate cron service with a securely
stored GitHub App installation token or fine-grained token; never put the token
in this repository. The token requires access to both repositories, contents write
for repository_dispatch, and actions write for workflow_dispatch. Run the following
requests at 02:30 and 04:00 Eastern, with a 04:40 recovery request if publication
is still incomplete. Use a scheduler supporting America/New_York and DST.

Main repository (CFB/NBA/CBB):

    POST https://api.github.com/repos/thomaspyrda/match-lab-college-football-data/dispatches
    Authorization: Bearer <secure token>
    Accept: application/vnd.github+json
    Content-Type: application/json

    {"event_type":"morning-refresh"}

NFL repository:

    POST https://api.github.com/repos/thomaspyrda/betwise-nfl-matchup-dashboard/actions/workflows/coordinate-nfl-daily.yml/dispatches
    Authorization: Bearer <secure token>
    Accept: application/vnd.github+json
    Content-Type: application/json

    {"ref":"main"}

A 204 response confirms request acceptance, not successful publication. Monitor
the coordinator and Verify and recover morning publication workflows. Do not
claim a 05:00 guarantee until the external clock is configured and overnight
publication is verified. NFL hosting remains on its existing deployment system;
the audit detects a lag rather than silently assuming bot commits were deployed.
