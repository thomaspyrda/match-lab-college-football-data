'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const original=fs.readFileSync(path.join(root,'sports-research/cbb-team-archive-v1.js'),'utf8');
const source=original.replace('const primary=loadArchive();','const primary=loadArchive();globalThis.auditPrimary=primary;');
const data=JSON.parse(fs.readFileSync(path.join(root,'data/cbb/teams/santa-clara-broncos.json'),'utf8'));
function setup(failures,pendingAux=false){
 let attempts=0,allow=false,retry;
 const main={innerHTML:'',setAttribute(){},querySelector(selector){
  if(selector==='h1')return {textContent:'Santa Clara Broncos'};
  if(selector==='.team-research-heading img')return {src:'logo'};
  if(selector==='#cbb-archive-retry')return {addEventListener(_,fn){retry=fn}};
  return {addEventListener(){}};
 }};
 const context=vm.createContext({document:{querySelector:()=>main},
  location:{pathname:'/cbb/teams/santa-clara-broncos/',search:''},URL,URLSearchParams,AbortController,
  console:{warn(){},error(){}},setTimeout(fn,ms){if(ms===15000)return 0;return setImmediate(fn)},clearTimeout(){},
  fetch:async url=>{
   if(url.includes('/data/cbb/teams/')){
    attempts++;
    if(!allow&&attempts<=failures)throw Error('temporary source failure');
    return {ok:true,json:async()=>JSON.parse(JSON.stringify(data))};
   }
   if(pendingAux)return new Promise(()=>{});
   return {ok:false,status:503,json:async()=>({})};
  }});
 new vm.Script(source).runInContext(context);
 return {main,context,attempts:()=>attempts,retry:async()=>{allow=true;await retry()}};
}
(async()=>{
 const transient=setup(1,true);
 await transient.context.auditPrimary;
 assert.equal(transient.attempts(),2,'Primary archive must retry a transient failure');
 assert(transient.main.innerHTML.includes('Season Snapshot'),'Slow optional sources must not block core archive');
 assert(!transient.main.innerHTML.includes('Data pending'));
 const unavailable=setup(99);
 await unavailable.context.auditPrimary;
 assert.equal(unavailable.attempts(),3,'Primary archive retries must be bounded');
 assert(unavailable.main.innerHTML.includes('cbb-archive-retry'),'Failed archive must offer retry');
 assert(!unavailable.main.innerHTML.includes('Data pending'),'Loading failure must not claim missing historical data');
 await unavailable.retry();
 assert(unavailable.main.innerHTML.includes('Season Snapshot'),'User retry must recover the saved archive');
 console.log('CBB loader retry, optional-source independence, failure state and recovery checks passed');
})().catch(error=>{console.error(error);process.exitCode=1});
