# Daily publication

The connected WiseStats daily scheduler starts the current `main` workflow at
02:30 America/New_York. It starts a separate afternoon cycle at 16:30. At 05:30
it checks progress and reports problems without starting recovery jobs.

`start-daily-primary.yml` is a small reusable launch point for that scheduler.
The scheduler writes a fresh Eastern-date request to `data/automation/primary-request.json`; that push starts a fresh launcher, which checks out current main and dispatches `coordinate-sport-data.yml` explicitly;
it never replays an old schedule's task selection. It refuses duplicate active
coordinators and duplicate successful cycles on the same Eastern date.

The coordinator checks authoritative completed-game sources first. Each sport's
statistics branch runs only for changed scores, unprocessed completed games, or
pending statistical inputs. Results precede boxes, player statistics, metrics,
rankings and derived pages. Independent sports run in parallel. Current injury,
roster, weather and market checks remain separate from season calculations.
MLB and historical backfills have no automatic schedules.

Watermarks advance only for successfully validated inputs. A source-check failure
cannot authorize an unchanged-data skip. A dated readiness receipt permits old
statistics only when a current authoritative check proves no new finals; old
statistics retain their actual collection timestamps. Prop Lab checks this
receipt and completed-game coverage before accepting unchanged statistics.

The coordinator makes one source publication handoff after its writers settle.
The publisher fingerprints public input files, publisher code, and the verified
Prop Lab release. Internal planning receipts do not invalidate that fingerprint.
An unchanged release skips assembly and deployment only after full live package
verification. A changed release must pass package and final Hostinger verification.

The coordinator explicitly dispatches Prop Lab after source publication is verified, including when an
unrelated source branch remains pending. Its existing per-event eligibility,
API budget, durable reservation and replay protections remain in force. A new
verified Prop Lab release triggers its own publication. Later 10:15 and 15:15
market scans remain available; there are no morning backup collectors.

The operational deadline is 06:00 Eastern. Missing provider data remains explicitly
pending and never replaces complete published statistics with incomplete values.
Runner queueing, unavailable feeds, and hosting failures are reported by the
05:30 check; scheduler acceptance alone is not proof of live publication.
