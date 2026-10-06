
const teamPageSlugs = {"2":"auburn","5":"uab","6":"south-alabama","8":"arkansas","9":"arizona-state","12":"arizona","16":"sacramento-state","21":"san-diego-state","23":"san-jos-state","24":"stanford","25":"california","26":"ucla","30":"usc","36":"colorado-state","38":"colorado","41":"connecticut","48":"delaware","52":"florida-state","55":"jacksonville-state","57":"florida","58":"south-florida","59":"georgia-tech","61":"georgia","62":"hawai-i","66":"iowa-state","68":"boise-state","77":"northwestern","84":"indiana","87":"notre-dame","96":"kentucky","97":"louisville","98":"western-kentucky","99":"lsu","103":"boston-college","113":"massachusetts","120":"maryland","127":"michigan-state","130":"michigan","135":"minnesota","142":"missouri","145":"mississippi","150":"duke","151":"east-carolina","152":"nc-state","153":"north-carolina","154":"wake-forest","158":"nebraska","164":"rutgers","166":"new-mexico-state","167":"new-mexico","183":"syracuse","189":"bowling-green","193":"miami-oh","194":"ohio-state","195":"ohio","197":"oklahoma-state","201":"oklahoma","202":"tulsa","204":"oregon-state","213":"penn-state","218":"temple","221":"pittsburgh","228":"clemson","235":"memphis","238":"vanderbilt","239":"baylor","242":"rice","245":"texas-a-m","248":"houston","249":"north-texas","251":"texas","252":"byu","254":"utah","256":"james-madison","258":"virginia","259":"virginia-tech","264":"washington","265":"washington-state","275":"wisconsin","276":"marshall","277":"west-virginia","278":"fresno-state","290":"georgia-southern","295":"old-dominion","309":"louisiana","324":"coastal-carolina","326":"texas-state","328":"utah-state","333":"alabama","338":"kennesaw-state","344":"mississippi-state","349":"army","356":"illinois","2005":"air-force","2006":"akron","2026":"app-state","2032":"arkansas-state","2050":"ball-state","2084":"buffalo","2116":"ucf","2117":"central-michigan","2132":"cincinnati","2199":"eastern-michigan","2226":"florida-atlantic","2229":"florida-international","2247":"georgia-state","2294":"iowa","2305":"kansas","2306":"kansas-state","2309":"kent-state","2335":"liberty","2348":"louisiana-tech","2390":"miami","2393":"middle-tennessee","2426":"navy","2429":"charlotte","2433":"ul-monroe","2439":"unlv","2440":"nevada","2449":"north-dakota-state","2459":"northern-illinois","2483":"oregon","2509":"purdue","2534":"sam-houston","2567":"smu","2572":"southern-miss","2579":"south-carolina","2623":"missouri-state","2628":"tcu","2633":"tennessee","2636":"texas-san-antonio","2638":"utep","2641":"texas-tech","2649":"toledo","2653":"troy","2655":"tulane","2711":"western-michigan","2751":"wyoming"};
function mainTeamLogo(t){const image=teamLogo(t),slug=teamPageSlugs[String(t.espn_id??t.id)]||Object.values(teamPageSlugs).find(s=>s===String(t.name).toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,""));return slug?`<a href="https://matchlab.parlaycalculator.bet/cfb/teams/${slug}/" aria-label="${esc(t.name)} team history" title="${esc(t.name)} team history" style="display:inline-flex;flex-shrink:0">${image}</a>`:image;}
const bottomMetricLabels = new Set(["Sack Rate Allowed","Havoc Allowed","Turnovers"]);
const orderMetrics = metrics => [...metrics].sort((a, b) => Number(bottomMetricLabels.has(a.label)) - Number(bottomMetricLabels.has(b.label)));
const $=s=>document.querySelector(s);
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
let dashboard,selectedGame,activeDay="all";
const hexRgb=h=>{const x=String(h||"").replace("#","");if(!/^[0-9a-f]{6}$/i.test(x))return null;return [0,2,4].map(i=>parseInt(x.slice(i,i+2),16))};
const isDark=h=>{const rgb=hexRgb(h);if(!rgb)return false;const [r,g,b]=rgb.map(v=>v/255);const lin=[r,g,b].map(v=>v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4));return .2126*lin[0]+.7152*lin[1]+.0722*lin[2]<.16};
const color=(t,i)=>{const primary=t.color,alt=t.alternate_color;if(primary&&isDark(primary)&&alt&&!isDark(alt))return alt;return primary||alt||(i===0?"#4aa8ff":"#9a78ff")};
const logo=t=>(isDark(t.color)&&t.alternate_logo)||t.logo||(t.espn_id?`https://a.espncdn.com/i/teamlogos/ncaa/500/${t.espn_id}.png`:"");
const abbr=t=>t.abbr||t.name.split(/\s+/).map(x=>x[0]).join("").slice(0,4).toUpperCase();
const teamLogo=(t,cls="team-logo")=>{const src=logo(t);if(!src)return"";if(isDark(t.color)&&!t.alternate_logo)return `<span class="${cls} recolor-logo" role="img" aria-label="${esc(t.name)} logo" style="--logo-url:url('${src}');--logo-color:${color(t,0)}"></span>`;return `<img class="${cls}" src="${src}" alt="${esc(t.name)} logo" loading="lazy">`};
const rank=v=>v==null?"—":"#"+Number(v);
const rawVal=(v,fmt)=>{if(v==null)return"—";const n=Number(v);if(!Number.isFinite(n))return"—";if(fmt==="percent")return (n*100).toFixed(1)+"%";if(fmt==="decimal")return n.toFixed(3);return String(v)};
const kickoff=g=>{if(!g.kickoff)return "Kickoff TBD";const d=new Date(g.kickoff);return new Intl.DateTimeFormat("en-US",{weekday:"short",hour:"numeric",minute:"2-digit",timeZone:"America/New_York",timeZoneName:"short"}).format(d)};
const spreadLabel=g=>{const s=Number(g.market?.spread);if(!Number.isFinite(s))return "—";if(s===0)return "PK";const team=s<0?abbr(g.home):abbr(g.away);return `${team} ${s>0?"+":""}${s}`};
const HELP={
"Sack Rate Allowed":"Sacks allowed divided by pass attempts plus sacks allowed. Lower is better.",
"Sack Rate":"Defensive sacks divided by opponent pass attempts plus sacks. Higher is better.",
"Havoc Allowed":"CFBD season havoc events allowed per offensive play: tackles for loss, passes defended and forced fumbles. Lower is better.",
"Havoc":"CFBD season havoc events created per opponent play: tackles for loss, passes defended and forced fumbles. Higher is better.",
"Turnovers":"Season giveaways (interceptions and lost fumbles) from official team box scores. Lower is better.",
"Turnovers Forced":"Season takeaways (opponent interceptions and lost fumbles) from official team box scores. Higher is better.",
"Success Rate":"Percentage of offensive plays considered successful by down and distance. Higher is better.",
"Defensive Success Rate":"Percentage of opponent plays considered successful by down and distance. Lower is better.",
"EPA / Play":"Average expected points added per offensive play. Higher is better.",
"EPA / Play Allowed":"Average expected points added by opponents per play. Lower is better.",
"Passing Success Rate":"Percentage of passing plays considered successful. Higher is better.",
"Defensive Pass Success Rate":"Percentage of opponent passing plays considered successful. Lower is better.",
"Rushing Success Rate":"Percentage of rushing plays considered successful. Higher is better.",
"Defensive Rush Success Rate":"Percentage of opponent rushing plays considered successful. Lower is better.",
"Explosiveness":"Average EPA generated on successful offensive plays. Higher means successful plays are more damaging.",
"Explosiveness Allowed":"Average EPA allowed on opponents' successful plays. Lower is better.",
"Points per Opportunity":"Average points scored after creating a scoring opportunity. Higher is better.",
"Points per Opportunity Allowed":"Average points allowed after opponents create scoring opportunities. Lower is better.",
"Third Down Conversion":"Percentage of offensive third downs converted. Higher is better.",
"Third Down Defense":"Percentage of opponent third downs converted. Lower is better.",
"Red Zone TD Rate":"Percentage of red-zone trips that end in touchdowns. Higher is better.",
"Red Zone TD Defense":"Percentage of opponent red-zone trips that end in touchdowns. Lower is better."
};
function season(t,i){const f=t.form||{};return `<article class="season-team" style="--team-color:${color(t,i)}"><div class="season-team-head">${teamLogo(t,"season-team-logo")}<b>${esc(abbr(t))}</b></div><div class="season-stats"><span><strong>${esc(t.record||"—")}</strong><small>Record</small></span><span><strong>${f.avg_points??"—"}</strong><small>PPG</small></span><span><strong>${f.avg_allowed??"—"}</strong><small>PPG Allowed</small></span></div></article>`}
function metricCard(m,type){
 const isOff=type==="offense";
 const kicker=isOff?"OFFENSE":"DEFENSE";
 const label=isOff?(m.offense_label||m.label):(m.defense_label||m.label);
 const values=[
   [selectedGame.away,0,isOff?m.away_offense:m.away_defense,isOff?m.away_offense_rank:m.away_defense_rank],
   [selectedGame.home,1,isOff?m.home_offense:m.home_defense,isOff?m.home_offense_rank:m.home_defense_rank]
 ];
 const line=([t,i,v,r])=>`<div class="metric-team" style="--team-color:${color(t,i)}"><span class="metric-team-name">${teamLogo(t,"metric-logo")}<b>${esc(abbr(t))}</b></span><span class="metric-number">${rawVal(v,m.format)}</span><span class="metric-rank"><b>${rank(r)}</b><small>FBS rank</small></span><span class="metric-track"><i style="width:${r==null?2:Math.max(2,Math.min(100,100-(Number(r)-1)/1.37))}%"></i></span></div>`;
 return `<article class="metric-card"><div class="metric-title"><span><small class="metric-kicker">${kicker} METRIC</small><span class="metric-name">${esc(label)}<button class="info" aria-label="About ${esc(label)}" data-tip="${esc(HELP[label]||"Current-season FBS statistic from CollegeFootballData.")}">?</button></span></span><span class="rank-heading"><i>SEASON STAT</i><b>FBS RANK</b></span></div>${values.map(line).join("")}</article>`
}
function pair(m){return metricCard(m,"offense")+metricCard(m,"defense")}
function marketTrendRow(t){
 return `<article class="trend-card"><div class="trend-card-head"><strong>${esc(t.label)}</strong><button class="info" data-tip="${esc(t.note||"Current-season betting result.")}" aria-label="About ${esc(t.label)}">?</button></div><div class="trend-values"><span style="--team-color:${color(selectedGame.away,0)}">${teamLogo(selectedGame.away,"trend-logo")}<b>${esc(t.away)}</b></span><i>VS</i><span style="--team-color:${color(selectedGame.home,1)}">${teamLogo(selectedGame.home,"trend-logo")}<b>${esc(t.home)}</b></span></div></article>`;
}
function marketResults(){
 const rows=selectedGame.market_trends||[];
 if(!rows.length)return"";
 return `<section class="trend-group"><div class="trend-group-title"><span>↗</span><h4>Market Results</h4></div><div class="trend-grid">${rows.map(marketTrendRow).join("")}</div></section>`;
}
const usagePct=v=>v==null?"—":`${Math.round((Number(v)<=1?Number(v)*100:Number(v))*10)/10}%`;
function qbEfficiency(player){
 const metric=player.efficiency;
 if(player.position!=="QB")return "";
 const value=metric?.value==null?"—":`${Number(metric.value)>=0?"+":""}${Number(metric.value).toFixed(3)}`;
 const rank=metric?.qualified&&metric.rank?`#${metric.rank} / ${metric.qualifying_count}`:"Not qualified";
 return `<div class="qb-efficiency"><div><small>${esc(metric?.label||"Passing PPA")}</small><strong>${value}</strong></div><div><small>QB RANK <button class="info" data-tip="${esc(metric?.help||"Rank appears after the quarterback meets the qualifying sample.")}" aria-label="About QB rank">?</button></small><strong>${rank}</strong></div></div>`;
}

function collegePlayerCard(player,team){
 const items=(player.usage||[]).map(item=>`<div class="usage"><b>${usagePct(item.value)}</b><span>${esc(item.label)}</span></div>`).join("");
 const pos=String(player.position||"").toUpperCase();
 const statLabels=pos==="QB"?["CMP","ATT","PASS YDS","PASS TD","INT","RUSH YDS"]:pos==="RB"?["RUSH","RUSH YDS","RUSH TD","REC","REC YDS","REC TD"]:["REC","REC YDS","REC TD","RUSH","RUSH YDS","RUSH TD"];
 const production=statLabels.map(label=>`<span><b>—</b><small>${label}</small><em>season stats pending</em></span>`).join("");
 const pending=player.placeholder?`<div class="availability-note"><b>Usage data:</b> Player usage will populate on the next successful season refresh.</div>`:"";
 return `<article class="player-card" style="--team-color:${color(team,team===selectedGame.away?0:1)}"><div class="player-top"><div class="player-identity">${teamLogo(team,"player-team-logo")}<div><span class="position">${esc(player.position||"—")} · ${esc(abbr(team))}</span><h3>${esc(player.name||"Usage data pending")}</h3></div></div><span class="subtle">${esc(player.slot||"Season usage")}</span></div>${pending}${player.availability_note?`<div class="availability-note">${esc(player.availability_note)}</div>`:""}${qbEfficiency(player)}<div class="production-line">${production}</div><div class="usage-label"><b>Opportunity share</b><button class="info" data-tip="Position-specific season opportunity metrics from CFBD. Skill players include Air Yards %; quarterbacks include 3rd Down Completion %." aria-label="About opportunity share">?</button></div><div class="usage-grid">${items||'<div class="usage"><b>—</b><span>Pending</span></div>'}</div></article>`;
}
function playerOpportunity(){
 const players=selectedGame.players||[];
 const half=players.length/2;
 return `<div class="players">${players.map((player,i)=>collegePlayerCard(player,i<half?selectedGame.away:selectedGame.home)).join("")}</div>`;
}
function formSchedule(){
 const fmt=t=>(t.form?.last_five||[]).map(x=>x.result).join(" · ")||"—";
 const compactOpp=x=>x.opponent_abbr||String(x.opponent||"").split(/\s+/).filter(Boolean).map(w=>w[0]).join("").slice(0,5).toUpperCase();
 const travel=t=>(t.form?.last_five||[]).map(x=>(x.location==="A"?"@":"")+compactOpp(x)).join(" · ")||"—";
 const rest=t=>{const games=(t.form?.last_five||[]).filter(x=>x.start_date);if(!games.length||!selectedGame.kickoff)return"—";const last=games.map(x=>new Date(x.start_date)).filter(d=>!Number.isNaN(d.getTime())).sort((a,b)=>b-a)[0];if(!last)return"—";const days=Math.max(0,Math.round((new Date(selectedGame.kickoff)-last)/86400000));return `${days} days`};
 const row=(label,a,h,note,seq=false)=>`<article class="context-card${seq?" context-card--sequence":""}"><strong>${label}</strong><div class="context-sides"><span style="--team-color:${color(selectedGame.away,0)}"><small>${esc(abbr(selectedGame.away))}</small><b>${esc(a)}</b></span><i>VS</i><span style="--team-color:${color(selectedGame.home,1)}"><small>${esc(abbr(selectedGame.home))}</small><b>${esc(h)}</b></span></div><p>${note}</p></article>`;
 return `<section class="context-panel"><div class="context-title"><span>◷</span><div><h4>Form & Schedule</h4><p>Recent results, recovery time and travel context at a glance.</p></div></div><div class="context-grid">${row("Last five games",fmt(selectedGame.away),fmt(selectedGame.home),"Last 5 Results",true)}${row("Rest before kickoff",rest(selectedGame.away),rest(selectedGame.home),"Days between each team's most recent completed game and kickoff.")}${row("Travel sequence",travel(selectedGame.away),travel(selectedGame.home),"Last 5 Game Locations",true)}${row("Game setting",selectedGame.context?.neutral_site?"Neutral": "Road",selectedGame.context?.neutral_site?"Neutral":"Home",selectedGame.context?.conference_game?"Conference matchup.":"Non-conference matchup.")}</div></section>`}
function feature(){const f=selectedGame.featured_mismatch;if(!f)return"";const off=f.side?.startsWith("away")?selectedGame.away:selectedGame.home,def=off===selectedGame.away?selectedGame.home:selectedGame.away;return `<section class="efficiency-feature"><div class="feature-head"><span>◎</span><div><p>FEATURED MATCHUP · LARGEST FBS-RANK GAP</p><h4>${esc(f.metric)}</h4></div></div><div class="feature-values"><span style="--team-color:${color(off,0)}">${teamLogo(off,"trend-logo")}<small>${esc(abbr(off))} · offense · FBS #${f.offense_rank??"—"}</small><b>${rawVal(f.offense_value,(selectedGame.matchup_metrics||[]).find(x=>x.label===f.metric)?.format)}</b></span><i>VS</i><span style="--team-color:${color(def,1)}">${teamLogo(def,"trend-logo")}<small>${esc(abbr(def))} · defense · FBS #${f.opponent_defense_rank??"—"}</small><b>${rawVal(f.opponent_defense_value,(selectedGame.matchup_metrics||[]).find(x=>x.label===f.metric)?.format)}</b></span></div><p><b>Why it matters:</b> This is the largest FBS-rank gap among the displayed source statistics. Rank gap: ${f.rank_gap} places.</p></section>`}
function factorSentence(t){
 if(t.type!=="matchup_edge"){
  if(t.type==="bounce_back")return `${t.team} is coming off a loss, making response and early-game execution an important situational factor.`;
  if(t.type==="ranked_context")return `${t.team} enters as the ranked team, increasing the importance of handling the road environment without giving away early possessions.`;
  if(t.type==="game_context")return t.detail==="conference matchup"?"Conference familiarity can reduce schematic surprises and make execution in high-leverage downs more important.":t.detail||"This game context could influence the matchup.";
  return t.detail||"This situational factor could influence the matchup.";
 }
 const row=(selectedGame.matchup_metrics||[]).find(m=>m.label===t.metric);
 const edgeTeam=t.team===selectedGame.away.name?selectedGame.away:selectedGame.home;
 const other=edgeTeam===selectedGame.away?selectedGame.home:selectedGame.away;
 if(!row)return `${edgeTeam.name}'s ${t.metric} advantage could help it control efficiency in this matchup.`;
 const offenseIsAway=t.offense_side==="away";
 const offenseTeam=offenseIsAway?selectedGame.away:selectedGame.home;
 const defenseTeam=offenseIsAway?selectedGame.home:selectedGame.away;
 const offRank=offenseIsAway?row.away_offense_rank:row.home_offense_rank;
 const defRank=offenseIsAway?row.home_defense_rank:row.away_defense_rank;
 const impact={
  "Success Rate":t.edge_unit==="offense"?"stay ahead of the chains and avoid obvious passing downs":"force more unsuccessful early-down plays and create longer conversion situations",
  "EPA / Play":t.edge_unit==="offense"?"create more scoring value per snap and punish inefficient possessions":"limit scoring value per snap and force the offense to sustain longer drives",
  "Passing Success Rate":t.edge_unit==="offense"?"complete efficient passes often enough to sustain drives and attack favorable coverage":"disrupt the passing game and force more low-efficiency throws or difficult third downs",
  "Rushing Success Rate":t.edge_unit==="offense"?"keep manageable down-and-distance situations and preserve play-action options":"make the run game inefficient and push the offense toward more predictable passing situations",
  "Explosiveness":t.edge_unit==="offense"?"generate chunk plays that shorten drives and create faster scoring opportunities":"limit chunk gains and make the offense execute consistently over longer drives",
  "Points per Opportunity":t.edge_unit==="offense"?"turn scoring chances into more points and capitalize when drives cross into scoring territory":"hold scoring opportunities to fewer points and keep drives from becoming touchdowns",
  "Third Down Conversion":t.edge_unit==="offense"?"extend drives and create additional possession and scoring volume":"get off the field more often and reduce the opponent's total scoring opportunities",
  "Red Zone TD Rate":t.edge_unit==="offense"?"finish red-zone possessions with touchdowns instead of settling for field goals":"force more red-zone possessions to end without touchdowns and compress the scoring margin"
 }[t.metric]||"turn that efficiency advantage into better down-and-distance outcomes";
 if(t.edge_unit==="offense")return `${edgeTeam.name}'s FBS #${offRank??"—"} ${t.metric} faces ${defenseTeam.name}'s FBS #${defRank??"—"} corresponding defense, an edge that could help ${edgeTeam.name} ${impact}.`;
 return `${edgeTeam.name}'s FBS #${defRank??"—"} corresponding defense faces ${offenseTeam.name}'s FBS #${offRank??"—"} ${t.metric}, an edge that could help ${edgeTeam.name} ${impact}.`;
}
function factors(){const items=(selectedGame.trends||[]).slice(0,8).map(t=>{let title=t.metric||"Game context",detail=factorSentence(t);return `<li><span>${t.type==="matchup_edge"?"↗":"!"}</span><p><small>${esc((t.type||"CONTEXT").replaceAll("_"," "))}</small><b>${esc(title)}</b><span class="factor-detail">${esc(detail)}</span></p></li>`}).join("");return `<section class="factor-panel"><div class="factor-heading"><div><p class="eyebrow">KEY MATCHUP FACTORS</p><h3>What deserves the closest attention</h3></div><span>Largest matchup discrepancies—not a prediction</span></div><ul>${items}</ul></section>`}
function renderDetail(){
 const g=selectedGame,m=g.market||{},ml=(m.away_moneyline!=null||m.home_moneyline!=null)?`ML ${abbr(g.away)} ${m.away_moneyline??"—"} · ${abbr(g.home)} ${m.home_moneyline??"—"}`:"ML —",markets=[`Spread ${spreadLabel(g)}`,`Total ${m.total??"—"}`,ml,g.weather?.summary||"Weather unavailable"].map(x=>`<span class="pill">${esc(x)}</span>`).join("");
 $("#gameDetail").innerHTML=`<div class="matchup-title"><div><p class="eyebrow">${kickoff(g)}</p><div class="matchup-teams"><span>${mainTeamLogo(g.away)}<b>${esc(g.away.name)}</b></span><i>at</i><span>${mainTeamLogo(g.home)}<b>${esc(g.home.name)}</b></span></div></div><div class="market-strip">${markets}</div></div>
 <section class="season-overview"><p>SEASON SNAPSHOT · COMPLETED GAMES</p><div class="season-overview-grid">${season(g.away,0)}${season(g.home,1)}</div></section>
 <section class="section"><div class="section-head"><div><p class="eyebrow">EFFICIENCY & FBS RANK</p><h3>How the teams compare</h3></div><span class="subtle">#1 = best in FBS</span></div><details class="reading-guide"><summary>How to read these numbers</summary><div><p><b>Season Stat</b> is the current raw season statistic from CollegeFootballData.</p><p><b>FBS Rank</b> shows where that exact statistic ranks across FBS teams.</p><p><b>Each row</b> pairs an offensive metric with its corresponding defensive metric.</p></div></details><div class="metric-columns-head"><span>OFFENSIVE METRICS</span><span>DEFENSIVE METRICS</span></div><div class="grid">${orderMetrics(g.matchup_metrics||[]).map(pair).join("")}</div></section>
 <section class="section">${feature()}</section>
 <section class="section"><div class="section-head"><div><p class="eyebrow">TRENDS & SITUATIONAL CONTEXT</p><h3>The matchup at a glance</h3></div><span class="subtle">Tap ? for definitions</span></div><div class="trend-groups">${marketResults()}${formSchedule()}</div></section>
 <section class="section">${factors()}</section>
 <section class="section"><div class="section-head section-head-solo"><div><p class="eyebrow">PLAYER OPPORTUNITY</p></div></div>${playerOpportunity()}</section>`}
function selectGame(id){selectedGame=dashboard.games.find(g=>String(g.game_id)===String(id));document.querySelectorAll(".game-card").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.id===String(id))));$("#gameDetail").hidden=false;renderDetail()}
const dayKey=g=>{if(!g.kickoff)return"tbd";return new Intl.DateTimeFormat("en-US",{weekday:"long",timeZone:"America/New_York"}).format(new Date(g.kickoff))};
function renderGameRail(){
 const games=activeDay==="all"?dashboard.games:dashboard.games.filter(g=>dayKey(g)===activeDay);
 $("#games").innerHTML=games.map(g=>`<button class="game-card" data-id="${g.game_id}" aria-pressed="${selectedGame&&String(selectedGame.game_id)===String(g.game_id)}"><span class="game-time">${kickoff(g)}</span><span class="teams"><span>${teamLogo(g.away,"rail-logo")}<b>${esc(g.away.name)}</b></span><span>${teamLogo(g.home,"rail-logo")}<b>${esc(g.home.name)}</b></span></span><span class="markets"><span>${esc(spreadLabel(g))}</span><span>O/U ${esc(g.market?.total??"—")}</span></span></button>`).join("")||'<p class="empty game-rail-empty">No games scheduled for this day.</p>';
 document.querySelectorAll(".game-card").forEach(b=>b.addEventListener("click",()=>selectGame(b.dataset.id)));
 $("#games").scrollTo({left:0,behavior:"auto"});
}
function renderDayFilters(){
 const days=[...new Set(dashboard.games.map(dayKey))];
 $("#dayFilters").innerHTML=[["all","All"],...days.map(d=>[d,d.slice(0,3)])].map(([key,label])=>`<button type="button" class="day-filter${activeDay===key?" active":""}" data-day="${esc(key)}">${esc(label)}</button>`).join("");
 document.querySelectorAll(".day-filter").forEach(b=>b.addEventListener("click",()=>{activeDay=b.dataset.day;renderDayFilters();renderGameRail()}));
}
function scrollGames(direction){const rail=$("#games");rail.scrollBy({left:direction*Math.max(280,rail.clientWidth*.72),behavior:"smooth"})}
function render(){const d=new Date(dashboard.slate.generated_at);$("#updated").textContent="Updated "+d.toLocaleString("en-US",{month:"short",day:"numeric",year:"numeric",hour:"numeric",minute:"2-digit",timeZone:"America/New_York",timeZoneName:"short"});renderDayFilters();renderGameRail();$("#gamesPrev").onclick=()=>scrollGames(-1);$("#gamesNext").onclick=()=>scrollGames(1);$("#gameDetail").hidden=true}
document.addEventListener("click",e=>{const b=e.target.closest(".info");if(!b||!window.matchMedia("(max-width:760px)").matches)return;e.preventDefault();let d=document.querySelector(".definition-dialog");if(!d){d=document.createElement("dialog");d.className="definition-dialog";d.innerHTML='<div class="definition-dialog-head"><strong></strong><button type="button">✕</button></div><p></p>';d.querySelector("button").onclick=()=>d.close();document.body.appendChild(d)}d.querySelector("strong").textContent=b.getAttribute("aria-label")?.replace(/^About /,"")||"Definition";d.querySelector("p").textContent=b.dataset.tip||"";d.showModal()});
fetch("data/dashboard.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Dashboard data unavailable");return r.json()}).then(x=>{dashboard=x;render()}).catch(e=>{$("#updated").textContent=e.message});

