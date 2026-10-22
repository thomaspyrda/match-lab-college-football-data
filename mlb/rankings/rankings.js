(()=>{"use strict";
const app=document.querySelector("#mlb-rankings-app");
if(!app)return;
const mode=app.dataset.rankingsMode||"overall";
const names={overall:"Overall Team Rankings",offense:"Batting Rankings",defense:"Pitching Rankings"};
const modelRankKey=mode;
const shortLabels={};
const h=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const metricHelp={rank:"Default category rank. Ties share a rank; sorting another column does not renumber the model ranks.",team:"MLB team; open its existing season archive.",record:"Regular-season wins and losses; ties shown only if present.",overall_sd:"Run differential per game compared with the unweighted team mean, in standard deviations. Higher is better.",offense_sd:"OPS compared with the unweighted team mean, in standard deviations. Higher is better.",defense_sd:"ERA compared with the unweighted team mean, in standard deviations. Positive means lower (better) ERA.",run_diff_per_game:"(Runs scored minus runs allowed) divided by completed regular-season games. Overall ranking input. Higher is better.",ops:"On-base percentage plus slugging percentage, summed from rounded source rates. Batting ranking input. Higher is better.",era:"Earned runs allowed per nine innings. Pitching ranking input. Lower is better.",whip:"Walks plus hits allowed per inning pitched. Lower is better.",batting_average:"Hits divided by at-bats.",on_base_percentage:"How often batters reach base, excluding errors and fielder’s choices.",slugging_percentage:"Total bases divided by at-bats.",home_runs:"Total regular-season home runs.",home_runs_per_game:"Home runs per completed game.",strikeout_rate:"Batting strikeouts as a percentage of plate appearances. Lower is better.",opponent_average:"Opponent batting average allowed. Lower is better.",strikeouts_per_9:"Pitching strikeouts per nine innings. Higher is better.",runs_per_game:"Total runs scored divided by completed games.",runs_allowed_per_game:"Total runs allowed divided by completed games. Includes unearned runs; lower is better.",games_played:"Completed regular-season games in the stored source archive.",runs_scored:"Regular-season runs scored.",runs_allowed:"Regular-season runs allowed."};
const visible={overall:["overall_sd","run_diff_per_game","runs_per_game","runs_allowed_per_game","ops","era","whip","games_played"],offense:["offense_sd","ops","runs_per_game","batting_average","on_base_percentage","slugging_percentage","home_runs","home_runs_per_game","strikeout_rate","games_played"],defense:["defense_sd","era","whip","runs_allowed_per_game","opponent_average","strikeouts_per_9","games_played"]};
let data=null,selectedYear=null;
function pretty(k){return data.metric_labels[k]||k}
function num(v){return v===null||v===undefined||v===""?null:Number(v)}
function fmt(v,k){
 if(v===null||v===undefined||!Number.isFinite(Number(v)))return "—";
 const n=Number(v);
 if(k.endsWith("_sd"))return (n>0?"+":"")+n.toFixed(2)+" SD";
 if(["ops","batting_average","on_base_percentage","slugging_percentage","opponent_average"].includes(k))return n.toFixed(3).replace(/^0/,"");
 if(k==="strikeout_rate")return n.toFixed(1)+"%";
 if(["home_runs","games_played","runs_scored","runs_allowed"].includes(k))return String(Math.round(n));
 if(k==="run_diff_per_game")return (n>0?"+":"")+n.toFixed(2);
 return n.toFixed(2);
}
function ratingValue(row,key){return key.endsWith("_sd")?row.ratings[key]:row.metrics[key]}
function buildUI(){
 const seasons=Object.entries(data.seasons).sort((a,b)=>Number(b[0])-Number(a[0]));

 app.innerHTML='<p class="eyebrow">BETWISE MLB · LIVE DATA</p><h1 id="rank-page-title"></h1><p class="page-intro">Compare all 30 MLB teams using completed regular-season performance. Overall: run differential per game. Batting: OPS. Pitching: ERA. No opponent-strength or ballpark adjustments.</p><div class="mlb-rank-season-control"><label for="mlb-rank-season">Choose season<select id="mlb-rank-season" aria-label="Select MLB season"></select></label></div><p id="rank-season-status" class="mlb-rank-status" hidden></p><div class="rank-hero"><img src="https://matchlab.parlaycalculator.bet/mlb/dashboard/hero.png?v=mlb-collage-20261015" alt="MLB players featured on the BetWise MLB Dashboard"></div><p class="rank-tabs-label">Explore MLB Rankings</p><nav class="rank-tabs" aria-label="MLB rankings"><a href="/mlb/rankings/"'+(mode==="overall"?' class="active" aria-current="page"':"")+'><span>Overall Team Rankings</span></a><a href="/mlb/batting-rankings/"'+(mode==="offense"?' class="active" aria-current="page"':"")+'><span>Batting Rankings</span></a><a href="/mlb/pitching-rankings/"'+(mode==="defense"?' class="active" aria-current="page"':"")+'><span>Pitching Rankings</span></a><a href="/mlb/season-leaders/"><span>Season Leaders</span></a></nav><div class="mlb-rank-filters"><label>League <select id="mlb-league"><option value="">All MLB</option><option>American League</option><option>National League</option></select></label><label>Find a team <input id="mlb-team-search" type="search" placeholder="Team name"></label></div><div class="data-table-wrap"><div class="mlb-rank-table-scroll" id="rank-table-scroll"><table class="mlb-rank-table"><thead id="rank-table-head"></thead><tbody id="rank-table-body"></tbody></table></div></div><p class="mlb-rank-source">Source: <a id="rank-source" target="_blank" rel="noopener noreferrer">MLB Stats API</a>. <span id="rank-source-note"></span> This describes season performance, not a prediction or betting recommendation.</p>';
 let activeColumn="rank",activeAscending=true;
 const seasonSelect=app.querySelector("#mlb-rank-season");
 const requestedSeason=new URLSearchParams(location.search).get("season");
 selectedYear=seasons.some(([year])=>year===requestedSeason)?requestedSeason:(data.seasons[data.default_season]?data.default_season:seasons[0][0]);
 seasonSelect.innerHTML=seasons.map(([year,season])=>'<option value="'+h(year)+'">'+h(season.label)+'</option>').join("");
 seasonSelect.value=selectedYear;
 seasonSelect.addEventListener("change",()=>{
  const next=seasonSelect.value;
  if(!data.seasons[next])return;
  selectedYear=next;
  activeColumn="rank";
  activeAscending=true;
  const url=new URL(location.href);
  url.searchParams.set("season",selectedYear);
  history.replaceState(null,"",url);
  render();
 });
 app.querySelector("#mlb-league").addEventListener("change",render);
 app.querySelector("#mlb-team-search").addEventListener("input",render);
 function syncTopScrollbar(){
  const wrapper=app.querySelector("#rank-table-scroll"),table=app.querySelector(".mlb-rank-table"),bar=app.querySelector(".mlb-rank-table-scrubber"),thumb=bar?.querySelector(".mlb-rank-table-thumb");
  if(!wrapper||!table||!bar||!thumb)return;
  const update=()=>{
   const maxScroll=Math.max(0,table.scrollWidth-wrapper.clientWidth);
   const trackWidth=bar.clientWidth||wrapper.clientWidth;
   const thumbWidth=maxScroll?Math.min(trackWidth,Math.max(44,trackWidth*wrapper.clientWidth/table.scrollWidth)):trackWidth;
   const maxThumb=Math.max(0,trackWidth-thumbWidth);
   thumb.style.width=thumbWidth+"px";
   thumb.style.transform="translateX("+(maxScroll?(wrapper.scrollLeft/maxScroll)*maxThumb:0)+"px)";
   bar.setAttribute("aria-valuemax",String(Math.round(maxScroll)));
   bar.setAttribute("aria-valuenow",String(Math.round(wrapper.scrollLeft)));
   bar.setAttribute("aria-disabled",maxScroll?"false":"true");
  };
  if(!wrapper.dataset.scrollSync){
   wrapper.dataset.scrollSync="true";
   wrapper.addEventListener("scroll",()=>{const current=app.querySelector(".mlb-rank-table-scrubber");if(current){const currentTable=app.querySelector(".mlb-rank-table");if(currentTable){const currentThumb=current.querySelector(".mlb-rank-table-thumb"),maxScroll=Math.max(0,currentTable.scrollWidth-wrapper.clientWidth),trackWidth=current.clientWidth||wrapper.clientWidth,thumbWidth=maxScroll?Math.min(trackWidth,Math.max(44,trackWidth*wrapper.clientWidth/currentTable.scrollWidth)):trackWidth,maxThumb=Math.max(0,trackWidth-thumbWidth);currentThumb.style.width=thumbWidth+"px";currentThumb.style.transform="translateX("+(maxScroll?(wrapper.scrollLeft/maxScroll)*maxThumb:0)+"px)";current.setAttribute("aria-valuenow",String(Math.round(wrapper.scrollLeft)))}}});
   window.addEventListener("resize",()=>{const current=app.querySelector(".mlb-rank-table-scrubber");if(current){const currentTable=app.querySelector(".mlb-rank-table");if(currentTable){const currentThumb=current.querySelector(".mlb-rank-table-thumb"),maxScroll=Math.max(0,currentTable.scrollWidth-wrapper.clientWidth),trackWidth=current.clientWidth||wrapper.clientWidth,thumbWidth=maxScroll?Math.min(trackWidth,Math.max(44,trackWidth*wrapper.clientWidth/currentTable.scrollWidth)):trackWidth,maxThumb=Math.max(0,trackWidth-thumbWidth);currentThumb.style.width=thumbWidth+"px";currentThumb.style.transform="translateX("+(maxScroll?(wrapper.scrollLeft/maxScroll)*maxThumb:0)+"px)";current.setAttribute("aria-valuemax",String(Math.round(maxScroll)));current.setAttribute("aria-valuenow",String(Math.round(wrapper.scrollLeft)))}}});
  }
  if(!bar.dataset.dragReady){
   bar.dataset.dragReady="true";
   let dragging=false,dragOffset=0;
   const setFromPointer=(clientX)=>{
    const rect=bar.getBoundingClientRect(),trackWidth=bar.clientWidth||rect.width,tableNow=app.querySelector(".mlb-rank-table"),maxScroll=Math.max(0,tableNow.scrollWidth-wrapper.clientWidth),thumbWidth=thumb.offsetWidth,maxThumb=Math.max(0,trackWidth-thumbWidth);
    if(!maxScroll||!maxThumb)return;
    const thumbLeft=Math.min(maxThumb,Math.max(0,clientX-rect.left-dragOffset));
    wrapper.scrollLeft=(thumbLeft/maxThumb)*maxScroll;
   };
   bar.addEventListener("pointerdown",event=>{
    if(event.button!==undefined&&event.button!==0)return;
    const rect=thumb.getBoundingClientRect(),onThumb=event.clientX>=rect.left&&event.clientX<=rect.right;
    dragging=true;dragOffset=onThumb?event.clientX-rect.left:thumb.offsetWidth/2;
    bar.classList.add("dragging");
    bar.setPointerCapture?.(event.pointerId);
    if(!onThumb)setFromPointer(event.clientX);
    event.preventDefault();
   });
   bar.addEventListener("pointermove",event=>{if(dragging)setFromPointer(event.clientX)});
   const stop=event=>{if(!dragging)return;dragging=false;bar.classList.remove("dragging");if(bar.hasPointerCapture?.(event.pointerId))bar.releasePointerCapture(event.pointerId)};
   bar.addEventListener("pointerup",stop);bar.addEventListener("pointercancel",stop);bar.addEventListener("lostpointercapture",stop);
   bar.addEventListener("keydown",event=>{const maxScroll=Math.max(0,table.scrollWidth-wrapper.clientWidth);if(event.key==="ArrowLeft"){wrapper.scrollLeft-=120;event.preventDefault()}else if(event.key==="ArrowRight"){wrapper.scrollLeft+=120;event.preventDefault()}else if(event.key==="Home"){wrapper.scrollLeft=0;event.preventDefault()}else if(event.key==="End"){wrapper.scrollLeft=maxScroll;event.preventDefault()}});
  }
  bar.style.width=wrapper.clientWidth+"px";
  update();
 }
 function render(){
  const season=data.seasons[selectedYear];if(!season)return;
  let rows=season.teams.slice();
  const league=app.querySelector("#mlb-league").value,query=app.querySelector("#mlb-team-search").value.trim().toLowerCase();
  rows=rows.filter(row=>(!league||row.conference===league)&&(!query||(row.team+" "+row.abbreviation).toLowerCase().includes(query)));
  rows=rows.map(row=>({...row,page_rank:num(row.ranks[modelRankKey])}));
  function valueFor(row,key){
   if(key==="team")return row.team;
   if(key==="rank")return num(row.page_rank);
   if(key==="record"){const m=String(row.record||"").match(/(\d+)\s*[-–]\s*(\d+)/);return m?Number(m[1])/(Number(m[1])+Number(m[2])||1):null}
   return num(ratingValue(row,key));
  }
  rows.sort((a,b)=>{const av=valueFor(a,activeColumn),bv=valueFor(b,activeColumn);if(typeof av==="string"&&typeof bv==="string"){const c=av.localeCompare(bv);return activeAscending?c:-c}if(av===null&&bv!==null)return 1;if(bv===null&&av!==null)return -1;if(av!==bv)return activeAscending?av-bv:bv-av;return a.team.localeCompare(b.team)});
  app.querySelector("#rank-page-title").textContent=season.label+" MLB "+names[mode];
  app.querySelector("#rank-source").href=season.source_url;
  app.querySelector("#rank-source").textContent=season.source_name||"MLB Stats API";
  app.querySelector("#rank-source-note").textContent=season.source_note||"";
  const status=app.querySelector("#rank-season-status");
  status.hidden=false;
  status.textContent="Regular season only · "+season.ranked_teams+" of 30 teams ranked · "+(season.status==="complete"?"Completed season":"Season to date")+(season.data_updated_at?" · Source checked "+new Date(season.data_updated_at).toLocaleString("en-US",{dateStyle:"medium",timeStyle:"short",timeZone:"America/New_York"})+" ET":"")+". Postseason results are excluded.";
  const cols=[{key:"rank",label:"Rank"},{key:"logo",label:""},{key:"team",label:"Team"},{key:"record",label:"Record"}];
  const keys=visible[mode]||visible.overall;
  keys.forEach(k=>cols.push({key:k,label:pretty(k)}));
  cols.forEach(c=>c.help=metricHelp[c.key]||("Selected-season "+pretty(c.key)+" value for this team."));
  app.querySelector("#rank-table-head").innerHTML='<tr>'+cols.map(c=>c.key==="logo"?'<th scope="col" class="mlb-logo-heading"><span class="mlb-sr-only">Team logo</span></th>':'<th scope="col" aria-sort="'+(activeColumn===c.key?(activeAscending?"ascending":"descending"):"none")+'"><div class="mlb-th-content"><button type="button" class="mlb-sort-button" data-sort-key="'+h(c.key)+'" aria-label="Sort by '+h(c.label)+'">'+h(c.label)+' <span class="mlb-sort-arrow" aria-hidden="true">'+(activeColumn===c.key?(activeAscending?"↑":"↓"):"↕\uFE0E")+'</span></button><span class="help-wrap"><button class="help-btn" type="button" aria-label="About '+h(c.label)+'" aria-expanded="false">?</button><span class="help-pop" role="tooltip">'+h(c.help)+'</span></span></div></th>').join("")+'</tr><tr class="mlb-scrollbar-row"><th class="mlb-scrollbar-cell" colspan="'+cols.length+'"><div class="mlb-rank-table-scrubber" role="scrollbar" aria-label="Scroll ranking table horizontally" aria-controls="rank-table-scroll" aria-orientation="horizontal" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0" tabindex="0"><span class="mlb-rank-table-thumb" aria-hidden="true"></span></div></th></tr>';
  app.querySelectorAll("#rank-table-head [data-sort-key]").forEach(button=>button.addEventListener("click",()=>{const key=button.dataset.sortKey;if(activeColumn===key)activeAscending=!activeAscending;else{activeColumn=key;activeAscending=key==="team"||key==="rank"?true:key==="record"?false:(data.lower_is_better||[]).includes(key)}render()}));
  app.querySelector("#rank-table-body").innerHTML=rows.map(row=>"<tr>"+cols.map(col=>{
   if(col.key==="rank")return "<td>"+(row.page_rank==null?"—":row.page_rank)+"</td>";
   if(col.key==="logo")return '<td class="mlb-rank-logo"><a href="/mlb/teams/'+h(row.slug)+'/" aria-label="'+h(row.team)+'"><img loading="lazy" src="'+h(row.logo)+'" alt=""></a></td>';
   if(col.key==="team")return '<td class="mlb-rank-name"><a class="mlb-rank-team" href="/mlb/teams/'+h(row.slug)+'/"><span>'+h(row.team)+'</span></a></td>';
   if(col.key==="record")return "<td>"+h(row.record||"—")+"</td>";

   const value=ratingValue(row,col.key);
   return "<td>"+h(fmt(value,col.key))+"</td>";
  }).join("")+"</tr>").join("")||'<tr><td colspan="'+cols.length+'">No teams available for this season.</td></tr>';
  syncTopScrollbar();
 }
 render();
}
document.addEventListener("click",function(event){
 const button=event.target.closest(".help-btn");
 document.querySelectorAll(".help-wrap.open").forEach(w=>{
  if(!button||w!==button.closest(".help-wrap")){
   w.classList.remove("open");
   w.querySelector(".help-btn")?.setAttribute("aria-expanded","false");
  }
 });
 if(!button)return;
 event.preventDefault();event.stopPropagation();
 const wrap=button.closest(".help-wrap"),isOpen=wrap.classList.toggle("open");
 button.setAttribute("aria-expanded",isOpen?"true":"false");
 if(isOpen){
  const pop=wrap.querySelector(".help-pop"),rect=button.getBoundingClientRect();
  pop.style.position="fixed";
  pop.style.left=Math.max(12,Math.min(window.innerWidth-262,rect.left))+"px";
  pop.style.top=(rect.bottom+8)+"px";
 }
});
document.addEventListener("keydown",event=>{
 if(event.key==="Escape")document.querySelectorAll(".help-wrap.open").forEach(w=>{
  w.classList.remove("open");
  w.querySelector(".help-btn")?.setAttribute("aria-expanded","false");
 });
});
fetch("/mlb/rankings/data/mlb-team-rankings.json?v=1",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("MLB ranking archive is not available");return r.json()}).then(d=>{data=d;buildUI()}).catch(()=>{app.innerHTML='<div class="mlb-rankings-error"><h1>'+h(names[mode])+'</h1><p>Ranking data is temporarily unavailable. Please refresh shortly.</p></div>'});
})();
