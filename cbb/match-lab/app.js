"use strict";
const byId=id=>document.getElementById(id);
const clean=s=>String(s??"—").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let games=[],selected=null,history=[],activeDay='all',logoByName={},frozenPreseason=new Map();
const requests=new Map();
async function load(url){if(requests.has(url))return requests.get(url);const pending=(async()=>{const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),45000);try{const r=await fetch(url,{cache:url.includes('stage-')?'force-cache':'no-cache',signal:controller.signal});if(!r.ok)throw Error(url+' unavailable');return await r.json()}finally{clearTimeout(timer)}})();requests.set(url,pending);try{return await pending}catch(e){requests.delete(url);throw e}}
let archiveSamples={},betwiseRanks=new Map();
async function loadBetwiseRanks(){
 const d=await load('/data/cbb/strength-rankings.json');
 if(!Array.isArray(d.teams)||d.teams.length<300)throw Error('Incomplete BetWise rankings');
 betwiseRanks=new Map(d.teams.map(t=>[String(t.team_id),{rank:num(t.rank),asOf:d.updated_at}]));
}
function attachBetwiseRank(t){
 const entry=betwiseRanks.get(String(t.id??t.team_id).replace(/^cbb:espn:/,''));
 return entry?{...t,profile:{...t.profile,betwise_rank:entry.rank,betwise_rank_as_of:entry.asOf}}:t;
}
function betwiseRank(t){return num(t?.profile?.betwise_rank??t?.betwise_rank)}
// Historical teams use only their recorded pregame ranks. Current BetWise ranks are never attached to archive teams.
function rankingProfile(t){return betwiseRank(t)??stat(t,'kenpom_rank')??preRank(t)}
function rankingSimilarity(g){
 let total=0,used=0;
 const add=(a,b,w,scale)=>{if(a===null||b===null)return;total+=w*Math.exp(-Math.abs(a-b)/scale);used+=w};
 for(const side of ['away','home']){
  // Each team's position matters, not just the average or gap between opponents.
  add(rankingProfile(selected[side]),rankingProfile(g[side]),2,55);
  add(preRank(selected[side]),preRank(g[side]),1,55);
 }
 const a=['away','home'].map(side=>rankingProfile(selected[side])),b=['away','home'].map(side=>rankingProfile(g[side]));
 if(a.every(v=>v!==null)&&b.every(v=>v!==null))add(a[0]-a[1],b[0]-b[1],1,65);
 return used?total/used:0;
}
function atsDecision(g){const hp=num(g.result?.home_points),ap=num(g.result?.away_points),spread=num(g.market?.spread??g.market?.home_spread);if(hp===null||ap===null||spread===null)return null;const margin=hp-ap+spread;return Math.abs(margin)<0.00001?'push':margin>0?'home':'away'}
async function loadHistory(){
 const index=await load('data/search-index.json');archiveSamples=index.samples;
 const counts=['away','home'].map(side=>num(selected[side]?.profile?.games)??0);
 const tol=counts.map(n=>n<5?3:n<12?4:6);
 const shardDistance=key=>key.split('-').reduce((sum,b,i)=>sum+Math.max(0,+b*4-counts[i],counts[i]-(+b*4+3))/tol[i],0);
 const keys=Object.keys(index.shards).sort((a,b)=>shardDistance(a)-shardDistance(b)||a.localeCompare(b));
 const initial=keys.filter(k=>shardDistance(k)===0); // Always include the complete nearby season-stage neighborhood.
 const rows=[],seen=new Set();
 const read=async batch=>{const data=await Promise.all(batch.map(k=>load('data/'+index.shards[k])));data.forEach(d=>d.games.forEach(g=>{const id=gameKey(g);if(!seen.has(id)){seen.add(id);rows.push(g)}}));await new Promise(r=>setTimeout(r,0))};
 for(let i=0;i<initial.length;i+=3)await read(initial.slice(i,i+3));
 const eligible=()=>rows.filter(g=>verified(g)&&date(g)<date(selected)&&['home','away'].includes(atsDecision(g))).length;
 const remaining=keys.filter(k=>!initial.includes(k));
 // Sparse stage neighborhoods expand outward, never manufacture or duplicate historical games.
 for(let i=0;eligible()<10&&i<remaining.length;i+=3)await read(remaining.slice(i,i+3));
 return rows;
}

const val=(x,...keys)=>keys.reduce((v,k)=>v?.[k],x);
const num=v=>v==null||v===""?null:Number.isFinite(+v)?+v:null;
function team(v){return typeof v==="string"?{name:v}:v||{name:"Unknown"}}
function gameKey(g){return String(g.id??g.game_id??[g.date,g.away?.name,g.home?.name].join("|"))}
function date(g){return Date.parse(g.date||g.kickoff||g.start_date||"")}
function name(g,side){return team(g[side]).name||"Unknown"}
function schedule(g){return g.metrics||[]}
function metric(g,k,side){const m=schedule(g).find(x=>x.key===k);return num(m?.[side]?.value??m?.[side]??team(g[side])?.profile?.metrics?.[k]??team(g[side])?.profile?.[k]??team(g[side])?.[k])}
const rankKey=s=>String(s||"").toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g," ").trim();
async function loadFrozenPreseason(){
 const data=await load("data/preseason-2027.json");
 if(data.season!=="2026-27"||data.frozen!==true||!Array.isArray(data.teams)||data.teams.length<360)throw Error("Incomplete 2026-27 opening rankings");
 const ranks=data.teams.map(t=>t.rank);
 if(new Set(ranks).size!==data.teams.length)throw Error("Duplicate frozen preseason rank");
 frozenPreseason=new Map();
 for(const entry of data.teams){
  // The dashboard uses full school + mascot names, while the frozen file often abbreviates schools.
  // Index both the official archive slug and short school name rather than guessing rank values.
  for(const value of [entry.name,entry.slug]){
   const key=rankKey(value);
   if(key)frozenPreseason.set(key,entry.rank);
  }
 }
}
function frozenRank(t){
 const keys=[t.school,t.name,t.display_name,t.displayName,t.short_name,t.slug,t.team_slug]
  .map(rankKey).filter(Boolean);
 for(const key of keys)if(frozenPreseason.has(key))return frozenPreseason.get(key);
 // A full team label may include a mascot not present in the school-only ranking name.
 // Require a word boundary and choose the longest known school key to avoid partial collisions.
 let best=null,bestLength=0;
 for(const key of keys){
  for(const [school,rank] of frozenPreseason){
   if(key.startsWith(school+" ")&&school.length>bestLength){best=rank;bestLength=school.length}
  }
 }
 return best;
}
function preRank(t){
 const p=t.profile||{};
 // Accept published preseason rankings; at opening tip the seeded team-strength
 // rank is a valid starting estimate, not an in-season performance statistic.
 const first=num(p.preseason_rank??t.preseason_rank??t.preseasonRank);
 if(first!==null&&first>=1)return first;
 // A team's 2026-27 preseason position stays frozen even after games begin.
 const starting=num(frozenRank(t));
 return starting!==null&&starting>=1?starting:null;
}
 const aliases={allowed_ppg:["allowed_ppg","ppg_allowed","allowed"],efg_pct:["efg_pct","efg","effective_field_goal_pct"],opp_efg_pct:["opp_efg_pct","opp_efg","opponent_efg_pct"],off_eff:["off_eff","adj_off_eff","offensive_efficiency","offensive_rating","off_rating","ortg"],def_eff:["def_eff","adj_def_eff","defensive_efficiency","defensive_rating","def_rating","drtg"],
 three_pct:["three_pct","three_point_pct","threePointFieldGoalPct"],opp_three_pct:["opp_three_pct","opponent_three_point_pct"],

 turnover_margin:["turnover_margin","turnoverMargin"],pace:["pace","avgEstimatedPossessions"],
 oreb_pg:["oreb_pg","offensive_rebounds_pg","avgOffensiveRebounds"],dreb_pg:["dreb_pg","defensive_rebounds_pg","avgDefensiveRebounds"],
 preseason_rank:["preseason_rank","preseasonRank"],strength_rank:["strength_rank","team_strength_rank","strengthRank"],kenpom_rank:["kenpom_rank","kenpomRank"],
 assists_pg:["assists_pg","avgAssists"],opp_assists_pg:["opp_assists_pg","assists_allowed_pg"],
 rest_days:["rest_days","days_rest"],ft_pct:["ft_pct","freeThrowPct"]};
 const stat=(t,key)=>{const profile=t?.profile||{};for(const k of aliases[key]||[key]){const v=num(profile.metrics?.[k]??profile[k]??t?.[k]);if(v!==null)return v}return null};

function context(g){const a=team(g.away),h=team(g.home),market=g.market||{};const diff=(x,y)=>x===null||y===null?null:x-y;const avg=(x,y)=>x===null||y===null?null:(x+y)/2;return {strength:diff(num(a.team_strength??a.strength_score),num(h.team_strength??h.strength_score)),off:diff(metric(g,"ortg","away"),metric(g,"ortg","home")),def:diff(metric(g,"drtg","away"),metric(g,"drtg","home")),pace:avg(metric(g,"pace","away"),metric(g,"pace","home")),spread:num(market.spread??market.home_spread),total:num(market.total),homePPG:num(h.ppg??h.profile?.ppg),awayPPG:num(a.ppg??a.profile?.ppg),homeAllowed:stat(h,"allowed_ppg"),awayAllowed:stat(a,"allowed_ppg"),homeForm:num(h.last5_win_pct??h.profile?.last5_win_pct),awayForm:num(a.last5_win_pct??a.profile?.last5_win_pct),conference:a.conference&&h.conference?Number(a.conference===h.conference):null,preseasonDiff:diff(preRank(a),preRank(h)),preseasonAvg:avg(preRank(a),preRank(h)),played:Math.min(num(a.profile?.games)??0,num(h.profile?.games)??0)}}
const weights={strength:[25,25],off:[12.5,20],def:[12.5,20],pace:[15,8],spread:[7.5,5],total:[7.5,8],homePPG:[7.5,12],awayPPG:[7.5,12],homeAllowed:[7.5,12],awayAllowed:[7.5,12],homeForm:[7.5,.4],awayForm:[7.5,.4],conference:[5,1]};
 // Similarity scores rely on dated pregame performance or an accepted preseason baseline; never on market totals alone.
function similarity(a,b){
 const opening=Math.min(a.played??0,12),anchor=Math.max(0,1-opening/12);
 const active={...weights,preseasonDiff:[25*anchor,65],preseasonAvg:[10*anchor,90]};
 let total=0,used=0;const full=Object.values(active).reduce((s,x)=>s+x[0],0);
 for(const [k,[w,scale]] of Object.entries(active)){const x=a[k],y=b[k];if(!Number.isFinite(x)||!Number.isFinite(y))continue;total+=w*Math.exp(-Math.abs(x-y)/scale);used+=w}
 const enoughPreseason=anchor>0.25&&Number.isFinite(a.preseasonDiff)&&Number.isFinite(b.preseasonDiff)&&Number.isFinite(a.preseasonAvg)&&Number.isFinite(b.preseasonAvg);
 const performanceEvidence=["strength","off","def","pace","homePPG","awayPPG","homeAllowed","awayAllowed"].some(k=>Number.isFinite(a[k])&&Number.isFinite(b[k]));
 if(!performanceEvidence&&!enoughPreseason)return null;
 if(used<15)return null;
 const coverage=used/full,raw=total/used;
 // Reliability penalty: limited contextual evidence must never produce near-perfect scores.
 // Display scale is deliberately calibrated, not a statistical probability.
 const score=Math.min(96,Math.round(100*raw*Math.pow(coverage,0.55)));
 return {score,coverage:used,coveragePct:Math.round(coverage*100),raw};
}
function verified(g){const r=g.result||{};if(r.verified!==true||g.pregame_verified!==true||!g.snapshot_as_of||!g.result_verified_at||!g.pregame_source||!g.result_source||!g.market_source)return false;const snapshot=Date.parse(g.snapshot_as_of),tip=date(g),finalized=Date.parse(g.result_verified_at);if(!Number.isFinite(snapshot)||!Number.isFinite(tip)||!Number.isFinite(finalized)||!(snapshot<tip&&tip<finalized))return false;const away=team(g.away),home=team(g.home);const keys=["team_strength","offensive_rating","defensive_rating","pace"];const available=keys.filter(k=>num(away[k]??away.profile?.[k])!==null&&num(home[k]??home.profile?.[k])!==null).length;const basic=[away,home].every(t=>num(t.profile?.ppg)!==null&&num(t.profile?.allowed_ppg)!==null&&num(t.profile?.games)>=1);if(available<2&&!basic)return false;const a=num(r.away_points),h=num(r.home_points),line=num(g.market?.total??g.over_under);if(a===null||h===null||line===null)return false;const outcome=a+h>line?"over":a+h<line?"under":"push";return String(r.total).toLowerCase()===outcome}
function day(g){return new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(date(g)))}
function upcomingSpread(g){const m=g.market||{},raw=m.spread??m.home_spread;if(raw==null||raw==="")return "Spread —";if(typeof raw==="string"&&/[a-z]/i.test(raw))return clean(raw);const n=num(raw);if(n===null)return "Spread —";const fav=n<=0?name(g,"home"):name(g,"away");const line=n<=0?n:-n;return clean(fav)+" "+(line>0?"+":"")+line}
function renderGames(){
 const dates=[...new Set(games.map(day))].sort();
 byId("dateFilters").innerHTML=[["all","All games"],...dates.map(x=>[x,new Date(x+"T12:00:00Z").toLocaleDateString("en-US",{timeZone:"America/New_York",weekday:"short",month:"short",day:"numeric"})])].map(([key,label])=>'<button type="button" data-day="'+key+'" class="'+(activeDay===key?"active":"")+'">'+clean(label)+'</button>').join("");
 byId("dateFilters").querySelectorAll("button").forEach(button=>button.onclick=()=>{activeDay=button.dataset.day;renderGames()});
 const filtered=games.filter(g=>activeDay==="all"||day(g)===activeDay);
 byId("scheduleStatus").textContent=filtered.length+" upcoming Division I games in the selected window";
 const image=t=>{const url=team(t).logo||team(t).logo_url;return /^https:\/\//.test(url||"")?'<img src="'+clean(url)+'" alt="" loading="lazy">':""};
 const card=g=>{
  try{
   const market=g.market||{};
   const logo=t=>{const url=team(t).logo||team(t).logo_url;return typeof url==="string"&&/^https:\/\//.test(url)?'<img src="'+clean(url)+'" alt="" loading="lazy">':""};
   const gameTime=new Date(date(g)).toLocaleString("en-US",{timeZone:"America/New_York",weekday:"short",month:"short",day:"numeric",hour:"numeric",minute:"2-digit"});
   return '<button class="game" data-id="'+clean(gameKey(g))+'" aria-pressed="'+Boolean(selected&&gameKey(selected)===gameKey(g))+'"><small>'+clean(gameTime)+'</small><strong>'+logo(g.away)+clean(name(g,"away"))+'</strong><strong>'+logo(g.home)+clean(name(g,"home"))+'</strong><small class="game-market-lines"><span>'+upcomingSpread(g)+'</span><span>O/U '+clean(market.total??"—")+'</span></small></button>';
  }catch(error){console.error("CBB Match Lab card error",g?.id,error);return '<button class="game" data-id="'+clean(gameKey(g))+'"><small>Upcoming game</small><strong>'+clean(name(g,"away"))+'</strong><strong>'+clean(name(g,"home"))+'</strong><small>Market unavailable</small></button>'}
 };
 byId("games").innerHTML=filtered.map(card).join("")||'<p class="muted">No upcoming games on this date.</p>';
 byId("games").querySelectorAll("button").forEach(button=>button.onclick=()=>{selected=games.find(g=>gameKey(g)===button.dataset.id);byId("see").disabled=false;byId("chosen").textContent=name(selected,"away")+" at "+name(selected,"home");byId("results").hidden=true;renderGames()})
}
document.querySelector(".rail-arrow.prev").onclick=()=>byId("games").scrollBy({left:-640,behavior:"smooth"});
document.querySelector(".rail-arrow.next").onclick=()=>byId("games").scrollBy({left:640,behavior:"smooth"});
function percentileValue(t,k){const v=stat(t,k),a=archiveSamples[k]||[];if(v===null||a.length<30)return null;let lo=0,hi=a.length;while(lo<hi){const mid=(lo+hi)>>1;if(a[mid]<v)lo=mid+1;else hi=mid}return 100*lo/a.length}
function metricDistance(g){
 let total=0,used=0,available=0;
 const metrics={ppg:1,allowed_ppg:1,off_eff:2,def_eff:2,efg_pct:1,opp_efg_pct:1,three_pct:1,opp_three_pct:1,turnover_margin:1,pace:1,margin:1,oreb_pg:.5,dreb_pg:.5,assists_pg:.5,opp_assists_pg:.5,ft_pct:.5};
 for(const side of ['away','home'])for(const [k,w] of Object.entries(metrics)){
  const a=percentileValue(selected[side],k),b=percentileValue(g[side],k);
  if(a===null)continue;available+=w;
  if(b===null){total+=50*w;continue}
  total+=Math.abs(a-b)*w;used+=w;
 }
 return {distance:available?total/available:50,coverage:available?used/available:0};
}
function rankMatch(g,researched){
 const metrics=metricDistance(g),base=similarity(researched,context(g));
 const gaps=['away','home'].map(side=>{const a=num(selected[side]?.profile?.games),b=num(g[side]?.profile?.games);return a===null||b===null?1:Math.abs(a-b)/(a<5?3:a<12?4:6)});
 const stage=Math.exp(-(gaps[0]+gaps[1])/2);
 const fingerprint=Math.exp(-metrics.distance/30)*Math.pow(metrics.coverage,.55);
 // Rank by unrounded similarity. Differences reduce scores, never exclude verified results.
 const ranking=rankingSimilarity(g);
 const quality=.55*ranking+.30*fingerprint+.10*stage+.05*(base?base.score/100:0);
 return {score:Math.max(0,Math.min(96,Math.round(100*quality))),quality,coverage:metrics.coverage,coveragePct:Math.round(100*metrics.coverage)};
}
function renderResults(){
 byId("results").hidden=false;
 const candidates=history.filter(verified).filter(g=>date(g)<date(selected));
 const researched=context(selected);
 const pool=candidates.filter(g=>["home","away"].includes(atsDecision(g))&&["over","under","push"].includes(String(g.result?.total).toLowerCase()))
  .map(g=>({g,match:rankMatch(g,researched)}))
  .sort((a,b)=>b.match.quality-a.match.quality||b.match.coverage-a.match.coverage||gameKey(a.g).localeCompare(gameKey(b.g)))
  .slice(0,10);
 const counts={over:0,under:0,push:0};
 pool.forEach(({g})=>counts[g.result.total]++);
 byId("status").textContent=pool.length+" closest verified historical comparisons · Match Scores prioritize team/preseason rankings, then statistical similarity, then season stage. Low scores indicate larger differences.";
 const covers={home:0,away:0};
 pool.forEach(({g})=>{covers[atsDecision(g)]++});
 const summary=[[String(covers.home),"Home covers"],[String(covers.away),"Away covers"],[counts.over+"–"+counts.under+(counts.push?"–"+counts.push:""),"Over–Under"],[String(pool.length),"Matches"]];
 byId("summary").innerHTML=summary.map(([v,l])=>'<div class="cbb-stat"><strong>'+v+'</strong><small>'+l+'</small></div>').join("");

 const logo=t=>{const url=t?.logo||t?.logo_url||logoByName[t?.name];return /^https:\/\//.test(url||"")?'<img class="cbb-match-logo" alt="" loading="lazy" src="'+clean(url)+'">':'<span class="cbb-match-logo placeholder" aria-hidden="true"></span>'};
 const fmt=v=>num(v)===null?"—":Number(v).toFixed(1);
 const signed=v=>num(v)===null?"—":(num(v)>0?"+":"")+num(v);
 const marketLine=(g)=>g.market?.spread??g.market?.home_spread??null;
 const spreadLabel=(g)=>{const raw=marketLine(g);if(raw==null||raw==="")return "Spread —";if(typeof raw==="string"&&/[a-z]/i.test(raw))return clean(raw);const line=num(raw);if(line===null)return "Spread —";const label=line<=0?team(g.home).name:team(g.away).name;return clean(label)+" "+signed(line<=0?line:-line)};
 const moneylineLabel=g=>{const m=g.market||{};const v=num(m.home_moneyline??m.home_ml??m.moneyline_home??m.homeMoneyline);const w=num(m.away_moneyline??m.away_ml??m.moneyline_away??m.awayMoneyline);if(v===null&&w===null)return 'Moneyline —';const useHome=w===null||(v!==null&&v<w);return clean(team(useHome?g.home:g.away).name)+' '+signed(useHome?v:w)};
 const teamSide=(t,mode="researched")=>{const historicalRank=num(t?.pregame?.kenpom_rank??t?.pregame_snapshot?.kenpom_rank??t?.snapshot?.kenpom_rank??t?.profile?.kenpom_rank_at_game??t?.kenpom_rank_at_game);const kenpom=mode==="historical"?(historicalRank??stat(t,"kenpom_rank")):stat(t,"kenpom_rank");const values=[["Preseason Rank",preRank(t)],["BetWise Rank",betwiseRank(t)],["KenPom Rank",kenpom]].filter(([,v])=>v!==null).map(([label,v])=>'<small>'+clean(label+" #"+v)+'</small>');const strength=num(t.team_strength??t.strength_score??t.profile?.team_strength??t.profile?.strength_score);return '<div class="cbb-team">'+logo(t)+'<div class="cbb-team-text"><strong>'+clean(t.name)+'</strong>'+values.join("")+(strength!==null?'<small>Team Strength '+clean(strength.toFixed(1).replace(/\.0$/,""))+'/100</small>':"")+'</div></div>'};
 const metricDefs=[
 ["PPG","ppg",false],["Opp PPG","allowed_ppg",true],
 ["Off Eff","off_eff",false],["Def Eff","def_eff",true],["3P%","three_pct",false],["Opp 3P%","opp_three_pct",true],
 ["eFG%","efg_pct",false],["Opp eFG%","opp_efg_pct",true],["TO Margin","turnover_margin",false],["Pace","pace",false],
 ["Off Reb/G","oreb_pg",false],["Def Reb/G","dreb_pg",false],["AST/G","assists_pg",false],["Opp AST/G","opp_assists_pg",true],
 ["FT%","ft_pct",false],
 
 ["Scoring Margin","margin",false]];
 // Rankings must be authentic dated pregame observations, never current/final ranks projected backwards.
 const samples={};
 const buildSamples=()=>{for(const [label,k] of metricDefs){samples[k]=archiveSamples[k]||history.flatMap(g=>[stat(team(g.away),k),stat(team(g.home),k)]).filter(v=>v!==null).sort((a,b)=>a-b)}};
 const percentile=(v,k,invert)=>{const arr=samples[k]||[];if(v===null||arr.length<30)return null;let lo=0,hi=arr.length;while(lo<hi){let mid=(lo+hi)>>1;if(arr[mid]<v)lo=mid+1;else hi=mid}const pct=100*lo/arr.length;return Math.round(invert?100-pct:pct)};
 buildSamples();
 const bars=(g)=>{const away=team(g.away),home=team(g.home);
 return '<div class="cbb-metric-title">PREGAME METRIC PERCENTILES</div><p class="cbb-note">Percentiles compare verified historical pregame values across the archive, when available (higher = stronger). Unavailable fields are shown as —; season-end figures are excluded.</p><div class="cbb-bars">'+metricDefs.map(([label,k,invert])=>{const av=stat(away,k),hv=stat(home,k),ap=percentile(av,k,invert),hp=percentile(hv,k,invert);if((k==="off_eff"||k==="def_eff")&&(ap===null||hp===null))return "";const val=v=>v===null?"—":String(v);const fill=v=>v===null?0:Math.max(1,Math.min(100,v));
 return '<div class="cbb-barrow"><span title="'+clean(label)+'">'+clean(label)+'</span><div class="cbb-barval"><i style="width:'+fill(ap)+'%"></i></div><b>'+val(ap)+'</b><b>'+val(hp)+'</b><div class="cbb-barval pink"><i style="width:'+fill(hp)+'%"></i></div></div>'}).join("")+'</div>'};
 const form=t=>{const p=t.profile||{},n=num(p.games),w=num(p.wins),l=num(p.losses),lw=num(p.last5_wins),ll=num(p.last5_losses);const overall=w!==null&&l!==null?w+'–'+l:n!==null&&num(p.win_pct)!==null?Math.round(n*num(p.win_pct))+'–'+Math.round(n*(1-num(p.win_pct))):'—';const last5=lw!==null&&ll!==null?lw+'–'+ll:n>0&&num(p.last5_win_pct)!==null?Math.round(Math.min(n,5)*num(p.last5_win_pct))+'–'+Math.round(Math.min(n,5)*(1-num(p.last5_win_pct))):'—';const rest=num(p.rest_days);return '<div class="cbb-form-tile"><b title="'+clean(t.name)+'">'+clean(t.name)+'</b><div class="cbb-form-rows"><span><small>Games Played</small><strong>'+(n===null?'—':n)+'</strong></span><span><small>Overall</small><strong>'+overall+'</strong></span><span><small>Last 5</small><strong>'+last5+'</strong></span><span><small>Rest Days</small><strong>'+(rest===null?'—':rest)+'</strong></span></div></div>'};
 const contextRows=g=>{const a=team(g.away),h=team(g.home);return [["Spread (home)",signed(marketLine(g))],["Game total",g.market?.total??"—"],["Away PPG",fmt(a.profile?.ppg)],["Home PPG",fmt(h.profile?.ppg)],["Away allowed",fmt(a.profile?.allowed_ppg)],["Home allowed",fmt(h.profile?.allowed_ppg)]]};
 const contextTable=(title,g)=>'<div class="cbb-context-table"><h4>'+title+'</h4>'+contextRows(g).map(([label,value])=>'<div><span>'+label+'</span><strong>'+clean(value)+'</strong></div>').join("")+'</div>';
 const sidePanel=(title,g,type)=>{const a=team(g.away),h=team(g.home);return '<section class="cbb-research-panel '+type+'"><div class="cbb-research-head"><b>'+title+'</b><small>'+clean(new Date(date(g)).toLocaleDateString("en-US",{month:"numeric",day:"numeric",year:"numeric"}))+'</small></div><div class="cbb-research-teams">'+teamSide(a,type)+'<span>@</span>'+teamSide(h,type)+'</div><div class="cbb-match-pills"><span>'+spreadLabel(g)+'</span><span>O/U '+clean(g.market?.total??"—")+'</span></div>'+bars(g)+'<div class="cbb-metric-title">SEASON-TO-DATE FORM (BEFORE TIPOFF)</div><div class="cbb-form-row">'+form(a)+form(h)+'</div></section>'};
 const explain=(researched,hist)=>{
  const x=context(researched),y=context(hist),matches=[],differences=[];
  // Only verified pregame observations are eligible; each item names both games' values.
  const add=(key,label,a,b,tolerance,unit="",digits=1)=>{
   if(!Number.isFinite(a)||!Number.isFinite(b))return;
   const delta=Math.abs(a-b),fmt=v=>Number(v).toFixed(digits)+(unit||"");
   const phrase=label+": researched "+fmt(a)+" vs historical "+fmt(b)+" (difference "+fmt(delta)+").";
   (delta<=tolerance?matches:differences).push({key,delta:delta/Math.max(tolerance,0.01),text:phrase});
  };
  const metricSpecs=[
   ["preseasonDiff","Preseason rank gap between opponents",22," ranks",0],
   ["preseasonAvg","Average preseason opponent ranking",32,"",0],
   ["strength","Away-minus-home Team Strength",11," pts"],
   ["off","Away-minus-home offensive efficiency",9,""],
   ["def","Away-minus-home defensive efficiency",9,""],
   ["pace","Combined matchup pace",5," poss."],
   ["spread","Home point spread",3.5," pts"],
   ["total","Posted game total",4.5," pts"],
   ["homePPG","Home scoring average",5," PPG"],
   ["awayPPG","Away scoring average",5," PPG"],
   ["homeAllowed","Home points allowed",5," PPG"],
   ["awayAllowed","Away points allowed",5," PPG"],
   ["homeForm","Home recent win rate",0.2,"",2],
   ["awayForm","Away recent win rate",0.2,"",2]
  ];
  metricSpecs.forEach(([k,label,tol,unit,precision])=>add(k,label,x[k],y[k],tol,unit,precision??1));
  const sideSpecs=[
   ["away","Away"],["home","Home"]
  ];
  const read=(t,k)=>stat(t,k);
  sideSpecs.forEach(([side,title])=>{
   const a=team(researched[side]),b=team(hist[side]);
   const specs=[
    ["strength_rank","Strength ranking",24,"",0],
    ["kenpom_rank","KenPom ranking",24,"",0],
    ["off_eff","Offensive efficiency",8,""],
    ["def_eff","Defensive efficiency",8,""],
    ["three_pct","Three-point percentage",4," percentage points"],
    ["opp_three_pct","Opp. three-point percentage",4," percentage points"],
    ["efg_pct","Effective FG percentage",4," percentage points"],
    ["opp_efg_pct","Opp. effective FG percentage",4," percentage points"],
    ["turnover_margin","Turnover margin",3,""],
    ["oreb_pg","Offensive rebounds per game",3,""],
    ["dreb_pg","Defensive rebounds per game",4,""],
    ["assists_pg","Assists per game",3,""],
    ["rest_days","Days of rest",2," days",0]
   ];
   specs.forEach(([k,label,tol,unit,precision])=>add(side+"-"+k,title+" "+label,read(a,k),read(b,k),tol,unit,precision??1));
   add(side+"-preseason",title+" preseason rank",preRank(a),preRank(b),28,"",0);
   add(side+"-ranking-profile",title+" ranking position (researched "+(betwiseRank(a)!==null?"BetWise":"preseason")+", historical "+(betwiseRank(b)!==null?"dated BetWise":stat(b,"kenpom_rank")!==null?"dated KenPom":"preseason")+")",rankingProfile(a),rankingProfile(b),28,"",0);
   add(side+"-games-played",title+" games played",num(a.profile?.games),num(b.profile?.games),3," games",0);
  });
  if(x.conference!==null&&y.conference!==null){
   const detail="Researched game "+(x.conference?"is":"is not")+" in-conference; historical game "+(y.conference?"is":"is not")+" in-conference.";
   (x.conference===y.conference?matches:differences).push({key:"conference",delta:x.conference===y.conference?0:10,text:detail});
  }
  // Rank facts by closeness and differences by divergence. One observation per unique key.
  const unique=arr=>[...new Map(arr.map(item=>[item.key,item])).values()];
  return {facts:unique(matches).sort((a,b)=>a.delta-b.delta).slice(0,5).map(v=>v.text),
          differences:unique(differences).sort((a,b)=>b.delta-a.delta).slice(0,5).map(v=>v.text)};
 };
 byId("matches").innerHTML=pool.map(({g,match},i)=>{
 const home=team(g.home),away=team(g.away),r=g.result||{},market=g.market||{},label=match.marketOnly?"MARKET ONLY":match.score>=80?"STRONG MATCH":match.score>=65?"CLOSE MATCH":"LIMITED MATCH";
 const reason=explain(selected,g);const point=(label,items)=>'<section class="cbb-reason-box"><h4>'+label+'</h4>'+(items.length?items.map(t=>'<p>'+clean(t)+'</p>').join(""):'<p>No sufficiently comparable verified metric available.</p>')+'</section>';
 const outcome=num(r.home_points)-num(r.away_points)+num(market.spread);const ats=Number.isFinite(outcome)?outcome>0?"HOME COVER":outcome<0?"AWAY COVER":"PUSH":"NOT AVAILABLE";
 return '<article class="cbb-match-card"><div class="cbb-match-top"><span>#'+(i+1)+' · '+clean(new Date(date(g)).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"}))+'</span><span class="cbb-match-score"><b>'+match.score+'</b> '+label+'</span></div>'+
 '<div class="cbb-match-teams">'+teamSide(away)+'<span class="cbb-at">at</span>'+teamSide(home)+'</div>'+
 '<div class="cbb-match-pills"><span>'+spreadLabel(g)+'</span><span>'+moneylineLabel(g)+'</span><span>O/U '+clean(market.total??"—")+'</span></div>'+
 '<details class="cbb-match-detail"><summary>Compare researched vs historical ↓</summary><div class="cbb-expanded"><div class="cbb-expanded-score"><small>MATCH SCORE</small><div><b>'+match.score+'</b><strong>'+label+'</strong></div><p>Pregame comparison only — not a predicted result.</p></div>'+
 
 '<div class="cbb-research-grid">'+sidePanel("RESEARCHED GAME",selected,"researched")+'<div class="cbb-versus">VS</div>'+sidePanel("HISTORICAL MATCH",g,"historical")+'</div>'+
 '<div class="cbb-reasons-grid">'+(match.marketOnly?reasonBox('MARKET-ONLY REFERENCE',['No preseason or in-season performance comparison is available.','Historical game total differs by '+match.totalDelta.toFixed(1)+' points.','This is not a statistically validated team matchup.']):reasonBoxPlaceholder(reason))+'</div>'+
 '<div class="cbb-outcome"><h3>WHAT HAPPENED</h3><strong>'+clean(r.away_points)+'–'+clean(r.home_points)+'</strong><p>'+clean(away.name)+' '+clean(r.away_points)+', '+clean(home.name)+' '+clean(r.home_points)+'</p><span>ATS: '+ats+' · TOTAL: '+clean(String(r.total).toUpperCase())+'</span></div>'+
 '<p class="cbb-detail-foot">Statistical coverage: '+match.coveragePct+'% of available researched metric weight. Low coverage limits match confidence. Similarity is not a probability.</p></div></details></article>';
 }).join("");
 if(!pool.length)byId("matches").innerHTML='<div class="cbb-research-grid">'+sidePanel("RESEARCHED GAME",selected,"researched")+'</div>';
 function reasonBoxPlaceholder(reason){return reasonBox("✓ WHY THESE GAMES MATCH",reason.facts)+reasonBox("⚠ KEY DIFFERENCES",reason.differences)+reasonBox("✧ THE BOTTOM LINE",[reason.facts.length>=4&&reason.differences.length>=4?reason.facts.length+" verified similarities and "+reason.differences.length+" meaningful differences identified. Compare both panels before interpreting the match score.":reason.facts.length+" verified similarities and "+reason.differences.length+" differences identified; fewer than four observations in either category limits a detailed comparison."])}
 function reasonBox(title,items){return '<section class="cbb-reason-box"><h4>'+title+'</h4>'+(items.length?items.map(t=>'<p>'+clean(t)+'</p>').join(""):'<p>Not enough common verified comparison data.</p>')+'</section>'}

 byId("results").scrollIntoView({behavior:"smooth",block:"start"});
}
(async()=>{try{const d=await load("data/upcoming.json").catch(()=>load("/cbb/dashboard/data/dashboard.json"));const raw=Array.isArray(d.games)?d.games:[];const now=Date.now();await Promise.all([loadFrozenPreseason().catch(error=>console.warn("Frozen preseason rankings unavailable",error)),loadBetwiseRanks().catch(error=>console.warn("BetWise rankings unavailable",error))]);games=raw.map(g=>({...g,away:typeof g.away==="string"?d.teams?.[g.away]||{name:g.away}:g.away,home:typeof g.home==="string"?d.teams?.[g.home]||{name:g.home}:g.home})).map(g=>({...g,away:attachBetwiseRank(g.away),home:attachBetwiseRank(g.home)})).filter(g=>Number.isFinite(date(g))&&date(g)>=now&&date(g)<now+7*86400000);renderGames()}catch(e){byId("games").innerHTML='<p class="muted">CBB schedule source unavailable. Historical results cannot be searched until the dashboard feed loads.</p>';console.error(e)}})();
byId("see").onclick=async()=>{if(!selected)return;byId("see").disabled=true;byId("see").textContent="FINDING MATCHES…";try{history=await loadHistory();await new Promise(r=>setTimeout(r,0));try{const logos=await load("data/team-logos.json");logoByName=logos.logos||{}}catch(e){console.warn("Logo registry unavailable",e)}renderResults()}catch(e){byId("results").hidden=false;byId("status").textContent="Verified historical archive not yet available. No unverified comparisons will be shown.";byId("summary").innerHTML="";byId("matches").innerHTML="";console.error(e)}finally{byId("see").textContent="SEE MATCHES";byId("see").disabled=false}};
