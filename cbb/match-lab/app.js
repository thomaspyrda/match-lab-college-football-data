"use strict";
const byId=id=>document.getElementById(id);
const clean=s=>String(s??"—").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let games=[],selected=null,history=[],activeDay='all',logoByName={};
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
 const covers={home:0,away:0,push:0,available:0};
 pool.forEach(({g})=>{const spread=num(g.market?.spread),hp=num(g.result?.home_points),ap=num(g.result?.away_points);if(spread===null||hp===null||ap===null)return;covers.available++;const margin=hp-ap+spread;if(margin>0)covers.home++;else if(margin<0)covers.away++;else covers.push++});
 const summary=[[covers.available?String(covers.home):"—","Home covers"],[covers.available?String(covers.away):"—","Away covers"],[counts.over+"–"+counts.under+(counts.push?" (+"+counts.push+" push)":""),"Over–Under"],[String(pool.length),"Matches"]];
 byId("summary").innerHTML=summary.map(([v,l])=>'<div class="cbb-stat"><strong>'+v+'</strong><small>'+l+'</small></div>').join("");

 const logo=t=>{const url=t?.logo||t?.logo_url||logoByName[t?.name];return /^https:\/\//.test(url||"")?'<img class="cbb-match-logo" alt="" loading="lazy" src="'+clean(url)+'">':'<span class="cbb-match-logo placeholder" aria-hidden="true"></span>'};
 const fmt=v=>num(v)===null?"—":Number(v).toFixed(1);
 const signed=v=>num(v)===null?"—":(num(v)>0?"+":"")+num(v);
 const marketLine=(g)=>g.market?.spread??g.market?.home_spread??null;
 const teamSide=t=>'<div class="cbb-team">'+logo(t)+'<div class="cbb-team-text"><strong>'+clean(t.name)+'</strong><small>'+clean(t.profile?.games??"—")+' prior games · '+fmt(t.profile?.ppg)+' PPG · '+fmt(t.profile?.allowed_ppg)+' allowed</small></div></div>';
 const bars=(g)=>{const away=team(g.away),home=team(g.home),rows=[["Points scored / game","ppg",120],["Points allowed / game","allowed_ppg",120],["Win percentage","win_pct",1],["Last 5 win percentage","last5_win_pct",1],["Scoring margin","margin",40]];
 return '<div class="cbb-metric-title">SEASON-TO-DATE PERFORMANCE (BEFORE TIPOFF)</div><p class="cbb-note">Only games completed before the historical matchup; higher values are not always better.</p><div class="cbb-bars">'+rows.filter(([label,k])=>num(away.profile?.[k])!==null&&num(home.profile?.[k])!==null).map(([label,k,max])=>{const av=num(away.profile[k]),hv=num(home.profile[k]);const pct=v=>Math.max(2,Math.min(100,(k==="margin"?(v+40)/80:v/max)*100));const value=v=>k.includes("pct")?Math.round(v*100)+"%":fmt(v);return '<div class="cbb-barrow"><span>'+label+'</span><div class="cbb-barval"><i style="width:'+pct(av)+'%"></i></div><b>'+value(av)+'</b><b>'+value(hv)+'</b><div class="cbb-barval pink"><i style="width:'+pct(hv)+'%"></i></div></div>'}).join("")+'</div>'};
 const form=t=>'<div class="cbb-form-tile"><b>'+clean(t.name)+'</b><small>'+clean(t.profile?.games??"—")+' prior games · '+Math.round((num(t.profile?.win_pct)||0)*100)+'% wins · '+fmt(t.profile?.ppg)+' scored · '+fmt(t.profile?.allowed_ppg)+' allowed</small></div>';
 const contextRows=g=>{const a=team(g.away),h=team(g.home);return [["Spread (home)",signed(marketLine(g))],["Game total",g.market?.total??"—"],["Away PPG",fmt(a.profile?.ppg)],["Home PPG",fmt(h.profile?.ppg)],["Away allowed",fmt(a.profile?.allowed_ppg)],["Home allowed",fmt(h.profile?.allowed_ppg)]]};
 const contextTable=(title,g)=>'<div class="cbb-context-table"><h4>'+title+'</h4>'+contextRows(g).map(([label,value])=>'<div><span>'+label+'</span><strong>'+clean(value)+'</strong></div>').join("")+'</div>';
 const sidePanel=(title,g,type)=>{const a=team(g.away),h=team(g.home);return '<section class="cbb-research-panel '+type+'"><div class="cbb-research-head"><b>'+title+'</b><small>'+clean(new Date(date(g)).toLocaleDateString("en-US",{month:"numeric",day:"numeric",year:"numeric"}))+'</small></div><div class="cbb-research-teams">'+teamSide(a)+'<span>@</span>'+teamSide(h)+'</div><div class="cbb-match-pills"><span>Home '+signed(marketLine(g))+'</span><span>O/U '+clean(g.market?.total??"—")+'</span></div>'+bars(g)+'<div class="cbb-metric-title">SEASON-TO-DATE FORM (BEFORE TIPOFF)</div><div class="cbb-form-row">'+form(a)+form(h)+'</div></section>'};
 const explain=(selected,hist)=>{const x=context(selected),y=context(hist),facts=[],differences=[];
 const compare=(k,label,tolerance,format)=>{if(!Number.isFinite(x[k])||!Number.isFinite(y[k]))return;const diff=Math.abs(x[k]-y[k]);const statement=label+" differ by "+diff.toFixed(1);(diff<=tolerance?facts:differences).push(statement)};
 compare("total","Totals",5);compare("spread","Home spreads",4);compare("homePPG","Home scoring averages",6);compare("awayPPG","Away scoring averages",6);compare("homeAllowed","Home points allowed",6);compare("awayAllowed","Away points allowed",6);
 return {facts,differences}};
 byId("matches").innerHTML=pool.map(({g,match},i)=>{
 const home=team(g.home),away=team(g.away),r=g.result||{},market=g.market||{},label=match.score>=80?"STRONG MATCH":match.score>=65?"CLOSE MATCH":"LIMITED MATCH";
 const reason=explain(selected,g);const point=(label,items)=>'<section class="cbb-reason-box"><h4>'+label+'</h4>'+(items.length?items.map(t=>'<p>'+clean(t)+'</p>').join(""):'<p>No sufficiently comparable verified metric available.</p>')+'</section>';
 const outcome=num(r.home_points)-num(r.away_points)+num(market.spread);const ats=Number.isFinite(outcome)?outcome>0?"HOME COVER":outcome<0?"AWAY COVER":"PUSH":"NOT AVAILABLE";
 return '<article class="cbb-match-card"><div class="cbb-match-top"><span>#'+(i+1)+' · '+clean(new Date(date(g)).toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric"}))+'</span><span class="cbb-match-score"><b>'+match.score+'</b> '+label+'</span></div>'+
 '<div class="cbb-match-teams">'+teamSide(away)+'<span class="cbb-at">at</span>'+teamSide(home)+'</div>'+
 '<div class="cbb-match-pills"><span>Home '+signed(market.spread)+'</span><span>O/U '+clean(market.total??"—")+'</span></div>'+
 '<details class="cbb-match-detail"><summary>Compare researched vs historical ↓</summary><div class="cbb-expanded"><div class="cbb-expanded-score"><small>MATCH SCORE</small><div><b>'+match.score+'</b><strong>'+label+'</strong></div><p>Pregame similarity only — not a predicted result.</p></div>'+
 '<div class="cbb-matchup-context"><h3>PREGAME MATCHUP CONTEXT</h3><p>Actual matching fields are listed; unavailable fields are never invented.</p><div class="cbb-context-grid">'+contextTable("RESEARCHED GAME",selected)+contextTable("HISTORICAL MATCH",g)+'</div></div>'+
 '<div class="cbb-research-grid">'+sidePanel("RESEARCHED GAME",selected,"researched")+'<div class="cbb-versus">VS</div>'+sidePanel("HISTORICAL MATCH",g,"historical")+'</div>'+
 '<div class="cbb-reasons-grid">'+reasonBoxPlaceholder(reason)+'</div>'+
 '<div class="cbb-outcome"><h3>WHAT HAPPENED</h3><strong>'+clean(r.away_points)+'–'+clean(r.home_points)+'</strong><p>'+clean(away.name)+' '+clean(r.away_points)+', '+clean(home.name)+' '+clean(r.home_points)+'</p><span>ATS: '+ats+' · TOTAL: '+clean(String(r.total).toUpperCase())+'</span></div>'+
 '<p class="cbb-detail-foot">Statistical coverage: '+match.coveragePct+'% of configured model factors. Low coverage limits match confidence. Similarity is not a probability.</p></div></details></article>';
 }).join("");
 function reasonBoxPlaceholder(reason){return reasonBox("✓ WHY THESE GAMES MATCH",reason.facts)+reasonBox("⚠ KEY DIFFERENCES",reason.differences)+reasonBox("✧ THE BOTTOM LINE",[reason.facts.length?"The available pregame statistics show some similarities; differences and missing information limit confidence.":"Too few verified fields are shared for a robust matchup comparison."])}
 function reasonBox(title,items){return '<section class="cbb-reason-box"><h4>'+title+'</h4>'+(items.length?items.map(t=>'<p>'+clean(t)+'</p>').join(""):'<p>Not enough common verified comparison data.</p>')+'</section>'}

 byId("results").scrollIntoView({behavior:"smooth",block:"start"});
}
(async()=>{try{const d=await load("/cbb/dashboard/data/dashboard.json");const raw=Array.isArray(d.games)?d.games:[];const now=Date.now();games=raw.map(g=>({...g,away:typeof g.away==="string"?d.teams?.[g.away]||{name:g.away}:g.away,home:typeof g.home==="string"?d.teams?.[g.home]||{name:g.home}:g.home})).filter(g=>Number.isFinite(date(g))&&date(g)>=now&&date(g)<now+7*86400000);renderGames()}catch(e){byId("games").innerHTML='<p class="muted">CBB schedule source unavailable. Historical results cannot be searched until the dashboard feed loads.</p>';console.error(e)}})();
byId("see").onclick=async()=>{if(!selected)return;byId("see").disabled=true;byId("see").textContent="FINDING MATCHES…";try{const d=await load("data/verified-historical.json");history=Array.isArray(d.games)?d.games:[];try{const registry=await load("/data/sports/team-registry.json");logoByName=Object.fromEntries((registry.teams||[]).filter(t=>t.sport==="cbb"&&t.logo).map(t=>[t.name,t.logo]))}catch(e){console.warn("Logo registry unavailable",e)}renderResults()}catch(e){byId("results").hidden=false;byId("status").textContent="Verified historical archive not yet available. No unverified comparisons will be shown.";byId("summary").innerHTML="";byId("matches").innerHTML="";console.error(e)}finally{byId("see").textContent="SEE MATCHES";byId("see").disabled=false}};
