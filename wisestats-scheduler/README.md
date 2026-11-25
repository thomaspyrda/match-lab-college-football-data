# WiseStats morning scheduler

This Cloudflare Worker submits the existing dated `morning` request to the sports repository. It has no HTTP route. Of its two UTC slots, only 2:30 a.m. America/New_York proceeds. On spring-forward day the 3:30 a.m. local slot substitutes for the missing 2:30 a.m. slot. Late events from another Eastern date or at or after 11 a.m. are ignored.

## Deployment and cutover

1. In GitHub, create a fine-grained token for `thomaspyrda/match-lab-college-football-data` only, with repository permissions **Contents: Read and write** and **Actions: Read-only**. No Workflows write permission is needed. Set an expiration and rotate the token before it expires.
2. From this directory, authenticate Wrangler to the intended Cloudflare account and use `npx wrangler secret put GITHUB_SCHEDULER_TOKEN`. Wrangler may offer to create the Worker if it doesn't exist yet. Enter the token at the prompt. Keep it out of source control and logs.
3. Run `npx wrangler deploy` from this directory. Confirm the two cron triggers and the secret binding for `wisestats-morning-scheduler` in Cloudflare.
4. At the next morning run, confirm Cloudflare reported that it submitted a dated request, a GitHub push-triggered launcher ran for that commit, and the coordinator and Hostinger verifier completed. If GitHub's native schedule starts first, the Worker skips the active or completed coordinator. Check the next run that the Worker launches before cutting over.
5. Remove just the native `schedule` block in `.github/workflows/start-daily-primary.yml` on `main`. Keep the dated request push trigger. Confirm the next run started from the Worker alone. A rollback re-adds the original GitHub `schedule` block and removes the Worker's cron triggers.
