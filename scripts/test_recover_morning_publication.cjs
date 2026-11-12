const assert = require('node:assert/strict');
const fs = require('node:fs');
const recover = require('./recover_morning_publication.cjs');
const now = new Date().toISOString();
const run = (id, status='completed', conclusion='success') => ({id, status, conclusion, head_branch:'main', event:'schedule', created_at:now, run_started_at:now, html_url:`run/${id}`});
const ready = () => Object.fromEntries(['cbb','cfb','nba','nfl'].map(s=>[s,{source:'ready',live:'ready'}]));
async function scenario(report, options={}) {
  const calls=[];
  const rs={
    'coordinate-sport-data.yml':options.sports || [run(1)],
    'run-nfl-public.yml':options.nfl || [run(2)],
    'publish-wisestats-public.yml':options.publish || [run(3)],
    'refresh-dashboard-availability.yml':[]
  };
  const github={rest:{actions:{
    listWorkflowRuns:async p=>({data:{workflow_runs:rs[p.workflow_id]}}),
    listJobsForWorkflowRun:()=>{},
    downloadJobLogsForWorkflowRun:async()=>({data:'Resolved NFL task: morning'}),
    reRunWorkflowFailedJobs:async p=>calls.push(['failed',p.run_id]),
    reRunJobForWorkflowRun:async p=>calls.push(['job',p.job_id]),
    createWorkflowDispatch:async p=>calls.push(['dispatch',p.workflow_id,p.inputs?.sport||p.inputs?.task])
  }},paginate:async(_,p)=>p.run_id===1?(options.jobs||[]):p.run_id===2?[{id:20,name:'process',conclusion:'success'},...(options.nflJobs||[])]:[{id:30,name:'publish'}]};
  const original=fs.readFileSync;
  fs.readFileSync=(p,...args)=>p==='sports-morning-report.json'?JSON.stringify(Object.fromEntries(Object.entries(report).filter(([s])=>s!=='nfl'))):p==='nfl-morning-report.json'?JSON.stringify({nfl:report.nfl}):original(p,...args);
  try {await recover({github,context:{repo:{owner:'x',repo:'y'}},core:{warning:()=>{},info:()=>{},setFailed:()=>{}}});}
  finally {fs.readFileSync=original;}
  return calls;
}
(async()=>{
  assert.deepEqual(await scenario(ready()),[]);
  let r=ready();r.nba.live='unchecked';assert.deepEqual(await scenario(r),[['job',30]]);
  assert.deepEqual(await scenario(r,{publish:[run(3,'in_progress',null)]}),[]);
  r=ready();r.cbb={source:'missing',live:'unchecked'};
  assert.deepEqual(await scenario(r),[['dispatch','coordinate-sport-data.yml','cbb']]);
  assert.deepEqual(await scenario(r,{sports:[run(1,'in_progress',null)]}),[]);
  assert.deepEqual(await scenario(r,{jobs:[{id:10,name:'cbb-boxes',conclusion:'failure'}]}),[['failed',1]]);
  r=ready();r.nba={source:'missing',live:'unchecked',error:'availability: delayed'};
  assert.deepEqual(await scenario(r),[['dispatch','refresh-dashboard-availability.yml',undefined]]);
  r=ready();assert.deepEqual(await scenario(r,{nflJobs:[{id:21,name:'Independent morning NFL injuries and weather',conclusion:'failure'}]}),[['failed',2]]);
  console.log('8 selective recovery scenarios passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
