"use strict";
const byId=id=>document.getElementById(id);
const clean=s=>String(s??"—").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let games=[],selected=null,history=[],activeDay='all';
async function load(url){const r=await fetch(url,{cache:"no-store"});if(!r.ok)throw Error(url+" unavailable");return r.json()}
const val=(x,...keys)=>keys.reduce((v,k)=>v?.[k],x);
const num=v=>v==null||v===""?null:Number.isFinite(+v)?+v:null;
function team(v){return typeof v==="string"?{name:v}:v||{name:"Unknown"}}
function gameKey(g){return String(g.id??g.game_id??[g.date,g.away?.name,g.home?.name].join("|"))}
function date(g){return Date.parse(g.date||g.kickoff||g.start_date||"")}
function name(g,side){return team(g[side]).name||"Unknown"}
function schedule(g){return g.metrics||[]}
function metric(g,k,side){const m=schedule(g).find(x=>x.key===k);return num(m?.[side]?.value??m?.[side]??team(g[side])?.profile?.[k]??team(g[side])?.[k])}
function context(g){const a=team(g.away),h=team(g.home),market=g.market||{};const diff=(x,y)=>x===null||y===null?null:x-y;const avg=(x,y)=>x===null||y===null?null:(x+y)/2;return {strength:diff(num(a.team_strength??a.strength_score),num(h.team_strength??h.strength_score)),off:diff(metric(g,"ortg","away"),metric(g,"ortg","home")),def:diff(metric(g,"drtg","away"),metric(g,"drtg","home")),pace:avg(metric(g,"pace","away"),metric(g,"pace","home")),spread:num(market.spread??market.home_spread),total:num(market.total),homePPG:num(h.ppg??h.profile?.ppg),awayPPG:num(a.ppg??a.profile?.ppg),homeAllowed:num(h.allowed_ppg??h.profile?.allowed_ppg),awayAllowed:num(a.allowed_ppg??a.profile?.allowed_ppg),homeForm:num(h.last5_win_pct??h.profile?.last5_win_pct),awayForm:num(a.last5_win_pct??a.profile?.last5_win_pct),conference:a.conference&&h.conference?Number(a.conference===h.conference):null}}
const weights={strength:[25,25],off:[12.5,20],def:[12.5,20],pace:[15,8],spread:[7.5,5],total:[7.5,8],homePPG:[7.5,12],awayPPG:[7.5,12],homeAllowed:[7.5,12],awayAllowed:[7.5,12],homeForm:[7.5,.4],awayForm:[7.5,.4],conference:[5,1]};
function similarity(a,b){
 let total=0,used=0;const full=Object.values(weights).reduce((s,x)=>s+x[0],0);
 for(const [k,[w,scale]] of Object.entries(weights)){const x=a[k],y=b[k];if(!Number.isFinite(x)||!Number.isFinite(y))continue;total+=w*Math.exp(-Math.abs(x-y)/scale);used+=w}
 if(used<7.5)return null;
 const coverage=used/full,raw=total/used;
 // Reliability penalty: limited contextual evidence must never produce near-perfect scores.
 // Display scale is deliberately calibrated, not a statistical probability.
 const score=Math.min(96,Math.round(100*raw*Math.pow(coverage,0.55)));
 return {score,coverage:used,coveragePct:Math.round(coverage*100),raw};
}
function verified(g){const r=g.result||{};if(r.verified!==true||g.pregame_verified!==true||!g.snapshot_as_of||!g.result_verified_at||!g.pregame_source||!g.result_source||!g.market_source)return false;const snapshot=Date.parse(g.snapshot_as_of),tip=date(g),finalized=Date.parse(g.result_verified_at);if(!Number.isFinite(snapshot)||!Number.isFinite(tip)||!Number.isFinite(finalized)||!(snapshot<tip&&tip<finalized))return false;const away=team(g.away),home=team(g.home);const keys=["team_strength","offensive_rating","defensive_rating","pace"];const available=keys.filter(k=>num(away[k]??away.profile?.[k])!==null&&num(home[k]??home.profile?.[k])!==null).length;const basic=[away,home].every(t=>num(t.profile?.ppg)!==null&&num(t.profile?.allowed_ppg)!==null&&num(t.profile?.games)>=5);if(available<2&&!basic)return false;const a=num(r.away_points),h=num(r.home_points),line=num(g.market?.total??g.over_under);if(a===null||h===null||line===null)return false;const outcome=a+h>line?"over":a+h<line?"under":"push";return String(r.total).toLowerCase()===outcome}
function day(g){return new Intl.DateTimeFormat("en-CA",{timeZone:"America/New_York",year:"numeric",month:"2-digit",day:"2-digit"}).format(new Date(date(g)))}
function renderGames(){
 const dates=[...new Set(games.map(day))].sort();
 byId("dateFilters").innerHTML=[["all","All games"],...dates.map(x=>[x,new Date(x+"T12:00:00Z").toLocaleDateString("en-US",{timeZone:"America/New_York",weekday:"short",month:"short",day:"numeric"})])].map(([key,label])=>'<button type="button" data-day="'+key+'" class="'+(activeDay===key?"active":"")+'">'+clean(label)+'</button>').join("");
 byId("dateFilters").querySelectorAll("button").forEach(button=>button.onclick=()=>{activeDay=button.dataset.day;renderGames()});
 const filtered=games.filter(g=>activeDay==="all"||day(g)===activeDay);
 byId("scheduleStatus").textContent=filtered.length+" upcoming Division I games in the selected window";
 const image=t=>{const url=team(t).logo||team(t).logo_url;return /^https:\/\//.test(url||"")?'<img src="'+clean(url)+'" alt="" loading="lazy">':""};
 byId("games").innerHTML=filtered.map(g=>'<button class="game" data-id="'+clean(gameKey(g))+'" aria-pressed="'+(selected&&gameKey(selected)===gameKey(g))+'"><small>'+clean(new Date(date(g)).toLocaleString("en-US",{timeZone:"America/New_York",weekday:"short",month:"short",day:"numeric",hour:"numeric",minute:"2-digit"}))+'</small><strong>'+image(g.away)+clean(name(g,"away"))+'</strong><strong>'+image(g.home)+clean(name(g,"home"))+'</strong><small>O/U '+clean(g.market?.total??"—")+'</small></button>').join("")||'<p class="muted">No upcoming games on this date.</p>';
 byId("games").querySelectorAll("button").forEach(button=>button.onclick=()=>{selected=games.find(g=>gameKey(g)===button.dataset.id);byId("see").disabled=false;byId("chosen").textContent=name(selected,"away")+" at "+name(selected,"home");byId("results").hidden=true;renderGames()})
}
document.querySelector(".rail-arrow.prev").onclick=()=>byId("games").scrollBy({left:-640,behavior:"smooth"});
document.querySelector(".rail-arrow.next").onclick=()=>byId("games").scrollBy({left:640,behavior:"smooth"});
function renderResults(){
 byId("results").hidden=false;
 const pool=history.filter(verified).filter(g=>date(g)<date(selected))
   .map(g=>({g,match:similarity(context(selected),context(g))}))
   .filter(x=>x.match!==null)
   .sort((a,b)=>b.match.score-a.match.score||b.match.coverage-a.match.coverage)
   .slice(0,10);
 const counts={over:0,under:0,push:0};
 pool.forEach(({g})=>counts[g.result.total]++);
 byId("status").textContent=pool.length?pool.length+" verified historical comparisons · Scores account for statistical coverage.":"No verified historical games share sufficient available pregame comparison fields.";
 const summary=[["—","Home covers"],["—","Away covers"],[counts.over+"–"+counts.under+(counts.push?" (+"+counts.push+" push)":""),"Over–Under"],[String(pool.length),"Matches"]];
 byId("summary").innerHTML=summary.map(([v,l])=>'<div class="cbb-stat"><strong>'+v+'</strong><small>'+l+'</small></div>').join("");
 const logo=t=>{const url=t?.logo||t?.logo_url;return /^https:\/\//.test(url||"")?'<img class="cbb-match-logo" alt="" loading="lazy" src="'+clean(url)+'">':'<span class="cbb-match-logo placeholder">●</span>'};
 const side=(t,profile)=>'<div class="cbb-team">'+logo(t)+'<div><strong>'+clean(t.name)+'</strong><small>Pregame: '+clean(profile?.games??"—")+' games · '+clean(profile?.ppg??"—")+' PPG · '+clean(profile?.allowed_ppg??"—")+' allowed</small></div></div>';
 byId("matches").innerHTML=pool.map(({g,match},i)=>{
   const home=team(g.home),away=team(g.away),market=g.market||{},r=g.result||{};
   const label=match.score>=80?"STRONG MATCH":match.score>=65?"CLOSE MATCH":"LIMITED MATCH";
   return '<article class="cbb-match-card"><div class="cbb-match-top"><span>#'+(i+1)+' · '+clean(new Date(date(g)).toLocaleDateString("en-US",{year:"numeric",month:"short",day:"numeric"}))+'</span><span class="cbb-match-score"><b>'+match.score+'</b> '+label+'</span></div>'+
   '<div class="cbb-match-teams">'+side(away,away.profile)+'<span class="cbb-at">at</span>'+side(home,home.profile)+'</div>'+
   '<div class="cbb-match-pills"><span>Home spread '+clean(market.spread??"—")+'</span><span>O/U '+clean(market.total??"—")+'</span><span>Final '+clean(r.away_points)+'–'+clean(r.home_points)+'</span><span>'+clean(String(r.total||"").toUpperCase())+'</span></div>'+
   '<details class="cbb-match-detail"><summary>Compare researched vs historical ↓</summary><div class="cbb-detail-grid"><div><b>Historical pregame</b><p>Away PPG: '+clean(away.profile?.ppg??"—")+' · Allowed: '+clean(away.profile?.allowed_ppg??"—")+'</p><p>Home PPG: '+clean(home.profile?.ppg??"—")+' · Allowed: '+clean(home.profile?.allowed_ppg??"—")+'</p></div><div><b>Historical result</b><p>'+clean(away.name)+' '+clean(r.away_points)+' · '+clean(home.name)+' '+clean(r.home_points)+'</p><p>Over/Under: '+clean(String(r.total||"").toUpperCase())+'</p></div></div><small>Comparison coverage: '+match.coveragePct+'% of configured factors. Closeness scores are relative indicators, not probabilities.</small></details></article>';
 }).join("");
 byId("results").scrollIntoView({behavior:"smooth",block:"start"});
}
(async()=>{try{const d=await load("/cbb/dashboard/data/dashboard.json");const raw=Array.isArray(d.games)?d.games:[];const now=Date.now();games=raw.map(g=>({...g,away:typeof g.away==="string"?d.teams?.[g.away]||{name:g.away}:g.away,home:typeof g.home==="string"?d.teams?.[g.home]||{name:g.home}:g.home})).filter(g=>Number.isFinite(date(g))&&date(g)>=now&&date(g)<now+7*86400000);renderGames()}catch(e){byId("games").innerHTML='<p class="muted">CBB schedule source unavailable. Historical results cannot be searched until the dashboard feed loads.</p>';console.error(e)}})();
byId("see").onclick=async()=>{if(!selected)return;byId("see").disabled=true;byId("see").textContent="FINDING MATCHES…";try{const d=await load("data/verified-historical.json");history=Array.isArray(d.games)?d.games:[];renderResults()}catch(e){byId("results").hidden=false;byId("status").textContent="Verified historical archive not yet available. No unverified comparisons will be shown.";byId("summary").innerHTML="";byId("matches").innerHTML="";console.error(e)}finally{byId("see").textContent="SEE MATCHES";byId("see").disabled=false}};
