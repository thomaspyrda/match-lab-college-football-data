# Daily publication

GitHub Actions starts current `main` once daily at 02:30 America/New_York.
The launcher dispatches the morning coordinator with the Eastern date and
refuses duplicates. A dated morning request file push can also use the launcher.

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
verified Prop Lab release triggers its own publication. Prop Lab requires today's
verified morning parent and has no independent collection schedule.

The target is 06:00 Eastern, with an 11:00 Eastern publication cutoff.
Missing provider data stays explicitly pending. The GitHub Actions run and
final Hostinger verification show publication status.
