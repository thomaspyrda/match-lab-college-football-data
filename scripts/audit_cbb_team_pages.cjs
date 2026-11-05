'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const read=(p,fallback={})=>{const file=path.join(root,p);return fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):fallback};
const renderer=fs.readFileSync(path.join(root,'sports-research/cbb-team-archive-v1.js'),'utf8');
let marker=renderer.indexOf('/* CBB_ARCHIVE_LOADER_START */');
if(marker<0)marker=renderer.lastIndexOf('Promise.all([fetch(');
assert(marker>0,'Cannot locate archive loader boundary');
const hook=`globalThis.auditRender=(input)=>{archive=input.archive;rankArchive=input.ranks;recruitArchive=input.recruits;conferenceResults=input.conference;tournamentResults=input.tournament;awardResults=input.awards;opponentMetrics=input.opponents;marketArchive=input.markets;pregameArchive=input.pregame;draftHistory=input.drafts;year=input.year;render();return main.innerHTML};})();`;
const compiled=new vm.Script(renderer.slice(0,marker)+hook,{filename:'cbb-team-archive-v1.js'});
const registry=read('data/sports/team-registry.json').teams.filter(t=>t.sport==='cbb');
const common={ranks:read('data/cbb/metric-ranks.json'),recruits:read('data/cbb/recruiting-classes.json'),
 conference:read('data/cbb/conference-tournament-results.json'),tournament:read('data/cbb/tournament-results.json'),
 awards:read('data/cbb/national-awards.json'),opponents:read('data/cbb/opponent-metrics.json'),
 pregame:read('data/cbb/pregame-markets/2027.json'),drafts:read('data/cbb/nba-draft-history.json')};
const failures=[],coverage={teams:0,seasons:0,currentSchedules:0,currentCompleted:0,currentPlayers:0,currentCoaches:0};
for(const team of registry){
 try{
  const archive=read('data/cbb/teams/'+team.slug+'.json',null);
  assert(archive&&archive.slug===team.slug,'Missing/misrouted archive');
  assert.strictEqual(String(archive.team_id),String(team.espn_id),'Wrong archive team ID');
  const page=fs.readFileSync(path.join(root,'cbb/teams',team.slug,'index.html'),'utf8');
  assert(page.includes('data-cbb-archive="v1"'),'Archive loader missing');
  assert.strictEqual((page.match(/<script[^>]*data-cbb-archive="v1"/g)||[]).length,1,'Duplicate archive scripts');
  if(process.argv.includes('--check-assets'))assert(page.includes('cbb-team-archive-v1.js?v=20261105-resilient-archives'),'Obsolete renderer version');
  const main={innerHTML:'',querySelector(selector){
   if(selector==='h1')return {textContent:team.name};
   if(selector==='.team-research-heading img')return {src:team.logo};
   if(selector==='#cbb-archive-year')return {addEventListener(){}};
   return null;
  }};
  const location={pathname:'/cbb/teams/'+team.slug+'/',search:'',href:'https://matchlab.parlaycalculator.bet/cbb/teams/'+team.slug+'/'};
  const context=vm.createContext({document:{querySelector:()=>main},location,URL,URLSearchParams,console});
  compiled.runInContext(context);
  const markets=read('data/cbb/markets/'+team.slug+'.json');
  for(const year of Object.keys(archive.seasons).sort()){
   try{
    const html=context.auditRender({...common,archive,markets,year});
    for(const id of ['snapshot','coaches','recruiting','schedule','metrics','players','accolades'])
     assert(html.includes('id="'+id+'"'),'Missing '+id+' section');
    assert(!html.includes('Team archive is temporarily unavailable'),'Fallback shown');
    coverage.seasons++;
   }catch(error){failures.push({team:team.slug,year,error:error.stack});}
  }
  const latest=archive.seasons['2027'];assert(latest,'Missing current season');
  const regular=latest.phases?.regular;assert(regular,'Missing current regular-season archive');
  coverage.teams++;
  coverage.currentSchedules+=Boolean(regular.games?.length);
  coverage.currentCompleted+=Boolean(regular.completed_games);
  coverage.currentPlayers+=Boolean(latest.players?.length||regular.players?.length);
  coverage.currentCoaches+=Boolean(latest.coaches?.length);
 }catch(error){failures.push({team:team.slug,error:error.stack});}
}
const report={coverage,failures};
console.log(JSON.stringify(report,null,2));
if(failures.length)process.exitCode=1;
