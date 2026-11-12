// Recover missing stages only; never restart collectors for hosting lag.
const fs = require('node:fs');

module.exports = async ({github, context, core}) => {
  const repo = context.repo;
  const activeStates = new Set(['queued', 'in_progress', 'waiting', 'pending', 'requested']);
  const cutoff = Date.now() - 30 * 86400000;
  const today = new Intl.DateTimeFormat('en-CA', {timeZone: 'America/New_York'}).format(new Date());
  const localDate = value => new Intl.DateTimeFormat('en-CA', {timeZone: 'America/New_York'}).format(new Date(value));
  const runs = async workflow_id => (await github.rest.actions.listWorkflowRuns({...repo, workflow_id, per_page: 100})).data.workflow_runs;
  const jobs = async run_id => github.paginate(github.rest.actions.listJobsForWorkflowRun, {...repo, run_id, per_page: 100});
  const freshRun = r => r.head_branch === 'main' && Date.parse(r.created_at) >= cutoff;
  const completed = rs => rs.filter(r => freshRun(r) && r.status === 'completed').sort((a,b) => Date.parse(b.run_started_at) - Date.parse(a.run_started_at));
  const active = rs => rs.some(r => freshRun(r) && activeStates.has(r.status));
  const read = name => JSON.parse(fs.readFileSync(name, 'utf8'));
  const report = {...read('sports-morning-report.json'), ...read('nfl-morning-report.json')};
  const [sportRuns, nflRuns, publisherRuns, availabilityRuns] = await Promise.all([
    runs('coordinate-sport-data.yml'), runs('run-nfl-public.yml'), runs('publish-wisestats-public.yml'), runs('refresh-dashboard-availability.yml')
  ]);
  let recovering = false;
  const eligible = completed(sportRuns).filter(r => ['schedule', 'repository_dispatch', 'push'].includes(r.event));
  const latest = eligible[0];
  if (!active(sportRuns)) {
    const latestJobs = latest ? await jobs(latest.id) : [];
    const failures = latestJobs.filter(j => j.conclusion === 'failure');
    const missing = ['cbb','cfb','nba'].filter(s => report[s]?.source !== 'ready' && !report[s]?.error?.startsWith('availability:'));
    if (failures.length && localDate(latest.run_started_at) === today && ['cbb','cfb','nba'].some(s => report[s]?.source !== 'ready')) {
      await github.rest.actions.reRunWorkflowFailedJobs({...repo, run_id: latest.id});
      core.warning(`Retrying failed sports stages: ${failures.map(j => j.name).join(', ')}. ${latest.html_url}`);
      recovering = true;
    } else {
      if (Object.values(report).some(s => s.error?.startsWith('availability:')) && !active(availabilityRuns)) {
        await github.rest.actions.createWorkflowDispatch({...repo, workflow_id: 'refresh-dashboard-availability.yml', ref: 'main'});
        core.warning('Recovering availability observations independently of statistical collectors.');
        recovering = true;
      }
      // A new explicitly scoped run preserves dependencies without repeating healthy sports.
      for (const sport of missing) {
        await github.rest.actions.createWorkflowDispatch({...repo, workflow_id: 'coordinate-sport-data.yml', ref: 'main', inputs: {sport}});
        core.warning(`Recovering ${sport} source inputs with an ordered ${sport}-only run.`);
        recovering = true;
      }
    }
  } else core.info('Sports coordinator active; no duplicate source recovery.');

  if (!active(nflRuns)) {
    let morning;
    let morningJobs;
    for (const r of completed(nflRuns)) {
      const js = await jobs(r.id);
      const p = js.find(j => j.name === 'process');
      if (!p) continue;
      const log = await github.rest.actions.downloadJobLogsForWorkflowRun({...repo, job_id: p.id});
      const text = typeof log.data === 'string' ? log.data : Buffer.from(log.data).toString('utf8');
      // Runtime marker is written after schedule-to-task mapping, including legacy runs.
      if (text.includes('Resolved NFL task: morning') ||
          (text.includes('NFL_TASK: morning') && !/NFL_SCHEDULE: (15 5,6|15 6|0 7|15 17|17 10|30 4,6,18|30 18) \*/.test(text))) {
        morning = r; morningJobs = js; break;
      }
    }
    if (morning && localDate(morning.run_started_at) === today && morningJobs.some(j => j.conclusion === 'failure')) {
      await github.rest.actions.reRunWorkflowFailedJobs({...repo, run_id: morning.id});
      core.warning(`Retrying failed NFL stages only. ${morning.html_url}`);
      recovering = true;
    } else if (report.nfl?.source !== 'ready') {
      await github.rest.actions.createWorkflowDispatch({...repo, workflow_id: 'run-nfl-public.yml', ref: 'main', inputs: {task: 'morning'}});
      core.warning('Recovering missing NFL morning source check and independent injuries/weather.');
      recovering = true;
    }
  } else core.info('NFL processing active; no duplicate recovery.');

  const sourceReady = ['cbb','cfb','nba','nfl'].every(s => report[s]?.source === 'ready');
  const liveReady = ['cbb','cfb','nba','nfl'].every(s => report[s]?.live === 'ready');
  if (!recovering && sourceReady && !liveReady && !active(publisherRuns) && !active(sportRuns) && !active(nflRuns)) {
    const pub = completed(publisherRuns)[0];
    const job = pub && (await jobs(pub.id)).find(j => j.name === 'publish');
    if (!job) throw new Error('No eligible public publisher recovery job under 30 days.');
    await github.rest.actions.reRunJobForWorkflowRun({...repo, job_id: job.id});
    core.warning(`Sources ready; retrying hosting publication only. ${pub.html_url}`);
  }
  if (!sourceReady || !liveReady || recovering) {
    core.setFailed('Morning publication is not yet fully verified. Recovery requests do not prove live publication.');
  } else core.info('All four sports have current source inputs and matching live files.');
};
