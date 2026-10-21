(()=>{"use strict";
const app=document.querySelector("#nba-rankings-app");
if(!app)return;
const mode=app.dataset.rankingsMode||"overall";
const names={overall:"Overall Team Rankings",offense:"Offensive Rankings",defense:"Defensive Rankings"};
const modelRankKey={overall:"overall",offense:"offense",defense:"defense"}[mode]||"overall";
const metricKeys={};
const shortLabels={offense_rating:"OFF vs Avg",defense_rating:"DEF vs Avg",orb_pct:"OFF Reb%",drb_pct:"DEF Reb%",ppg_allowed_home:"Home PPG Allowed",ppg_allowed_away:"Away PPG Allowed",opponent_assists_per_game:"Opp AST/G",opponent_turnovers_per_game:"Opp TOV/G",opponent_steals_per_game:"Opp STL/G",opponent_blocks_per_game:"Opp BLK/G",opp_ft_made_rate:"Opp FT/FGA",defensive_rebound_rate:"DEF Reb%",steals_per_game:"STL/G",blocks_per_game:"BLK/G",ppg:"PPG",ppg_home:"Home PPG",ppg_away:"Away PPG",ppg_allowed:"PPG Allowed",fg_pct:"FG%",opp_fg_pct:"Opp FG%",three_pct:"3P%",opp_three_pct:"Opp 3P%",offensive_rebound_rate:"OFF Reb%",defensive_rebound_rate:"DEF Reb%",assists_per_game:"AST/G",turnovers_per_game:"TOV/G",turnover_margin:"TOV Margin",rebounds_per_game:"REB/G",rebounds_allowed_per_game:"REB Allowed/G",ortg:"OFF Rating",drtg:"DEF Rating",offense_rating:"OFF vs Avg",defense_rating:"DEF vs Avg",overall_sd:"Overall SD",offense_sd:"OFF SD",defense_sd:"DEF SD",overall_rating:"Overall Rating",net_rating:"Net Rating",efg_pct:"eFG%",opp_efg_pct:"Opp eFG%",ts_pct:"TS%",ft_pct:"FT%",three_attempt_rate:"3P Att%",ft_rate:"FT Rate",ft_made_rate:"FT Made/FGA",tov_pct:"TOV%",opp_tov_pct:"Opp TOV%",steals_per_game:"STL/G",blocks_per_game:"BLK/G",opponent_assists_per_game:"Opp AST/G",opponent_turnovers_per_game:"Opp TOV/G",opponent_steals_per_game:"Opp STL/G",opponent_blocks_per_game:"Opp BLK/G",rim_fg_pct:"At-Rim FG%",opp_rim_fg_pct:"Opp At-Rim FG%",orb_pct:"OFF Reb%",drb_pct:"DEF Reb%",opp_tov_pct:"Opp TOV%"};
const h=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pctKeys=new Set(["fg_pct","opp_fg_pct","three_pct","opp_three_pct","orb_pct","drb_pct","offensive_rebound_rate","defensive_rebound_rate","efg_pct","opp_efg_pct","ts_pct","ft_pct","three_attempt_rate","ft_rate","ft_made_rate","tov_pct","opp_tov_pct","rim_fg_pct","opp_rim_fg_pct"]);
const signedKeys=new Set(["turnover_margin","overall_rating","offense_rating","defense_rating","net_rating"]);
const ratingKeys=new Set(["overall_rating","offense_rating","defense_rating","ortg","drtg","net_rating"]);
const visible={
overall:["overall_sd","ortg","drtg","net_rating","ppg","ppg_allowed","pace"],
offense:["offense_sd","offense_rating","ortg","ppg","ppg_home","ppg_away","fg_pct","three_pct","efg_pct","ts_pct","ft_pct","three_attempt_rate","ft_rate","ft_made_rate","assists_per_game","turnovers_per_game","tov_pct","turnover_margin","rebounds_per_game","orb_pct","pace"],
defense:["defense_sd","defense_rating","drtg","ppg_allowed","ppg_allowed_home","ppg_allowed_away","opp_fg_pct","opp_three_pct","opp_efg_pct","opp_rim_fg_pct","opp_ft_made_rate","opp_tov_pct","rebounds_allowed_per_game","opponent_assists_per_game","opponent_turnovers_per_game","opponent_steals_per_game","opponent_blocks_per_game","steals_per_game","blocks_per_game","drb_pct","defensive_rebound_rate","turnover_margin","pace"]
};
const metricHelp={"rank":"The team’s position in this ranking model for the selected season.","team":"NBA team name. This column stays visible while scrolling across the table.","record":"Regular-season wins and losses for the selected season.","overall_sd":"Net rating measured in standard deviations from the league average.","offense_rating":"Team offensive rating minus league-average offensive rating, in points per 100 possessions.","defense_rating":"League-average defensive rating minus team defensive rating, in points per 100 possessions; positive is better defense.","offense_sd":"Offensive rating versus league average, measured in standard deviations. Higher is better.","defense_sd":"Defensive rating versus league average, measured in standard deviations. Higher means better defense.","ortg":"Points scored per 100 estimated possessions. Higher is better.","drtg":"Points allowed per 100 estimated possessions. Lower is better.","net_rating":"Points scored minus points allowed per 100 possessions (OFF Rating minus DEF Rating).","pace":"Estimated possessions per 48 minutes.","ppg":"Average points scored per game.","ppg_home":"Average points scored per game at home.","ppg_away":"Average points scored per game on the road.","ppg_allowed":"Average points allowed per game.","ppg_allowed_home":"Average points allowed per game at home.","ppg_allowed_away":"Average points allowed per game on the road.","ppg_allowed_home":"Average points allowed per game at home.","ppg_allowed_away":"Average points allowed per game on the road.","fg_pct":"Field goals made as a percentage of field-goal attempts.","opp_fg_pct":"Opponent field goals made as a percentage of attempts. Lower is better.","three_pct":"Three-pointers made as a percentage of three-point attempts.","opp_three_pct":"Opponent three-pointers made as a percentage of attempts. Lower is better.","assists_per_game":"Average assists per game.","turnovers_per_game":"Average turnovers committed per game. Lower is better.","turnover_margin":"Opponent turnovers per game minus team turnovers per game. Positive means the team forces more turnovers than it commits.","rebounds_per_game":"Average total rebounds per game.","rebounds_allowed_per_game":"Average rebounds allowed per game.","offensive_rebound_rate":"Share of available offensive rebounds collected.","defensive_rebound_rate":"Share of available defensive rebounds collected.","efg_pct":"Effective field-goal percentage, accounting for the extra value of made three-pointers.","opp_efg_pct":"Opponent effective field-goal percentage. Lower is better.","ts_pct":"True shooting percentage, accounting for field goals, three-pointers, and free throws.","ft_pct":"Free throws made as a percentage of attempts.","three_attempt_rate":"Three-point attempts as a share of all field-goal attempts.","ft_rate":"Free-throw attempts relative to field-goal attempts.","ft_made_rate":"Free throws made per field-goal attempt.","tov_pct":"Percentage of team plays that end in a turnover. Lower is better.","opp_tov_pct":"Opponent turnover percentage.","steals_per_game":"Average steals per game.","blocks_per_game":"Average blocks per game.","opponent_assists_per_game":"Average assists allowed per game.","opponent_turnovers_per_game":"Average opponent turnovers per game.","opponent_steals_per_game":"Average steals allowed per game.","opponent_blocks_per_game":"Average blocks allowed per game.","opp_ft_made_rate":"Opponent free throws made per field-goal attempt.","orb_pct":"Share of available offensive rebounds collected.","drb_pct":"Share of available defensive rebounds collected.","rim_fg_pct":"Field-goal percentage on attempts at the rim.","opp_rim_fg_pct":"Opponent field-goal percentage at the rim. Lower is better.","offense_rating":"Team offensive rating minus league-average offensive rating, in points per 100 possessions.","defense_rating":"League-average defensive rating minus team defensive rating, in points per 100 possessions; positive is better."};
const directions={};
let data=null,selectedYear=null;
function pretty(k){return shortLabels[k]||data.metric_labels[k]||k.replace(/_/g," ").replace(/\b\w/g,x=>x.toUpperCase())}
function num(v){return v===null||v===undefined||v===""?null:Number(v)}
function fmt(v,k){
 if(v===null||v===undefined||!Number.isFinite(Number(v)))return "—";
 const n=Number(v);
 if(pctKeys.has(k))return n.toFixed(1)+"%";
 if(k==="overall_sd"||k==="offense_sd"||k==="defense_sd")return (n>0?"+":"")+n.toFixed(2)+" SD";
 if(signedKeys.has(k))return (n>0?"+":"")+n.toFixed(1);
 if(k==="games_played")return String(Math.round(n));
 return n.toFixed(ratingKeys.has(k)?1:1);
}
function ratingValue(row,key){
 if(key==="overall_sd")return row.ratings.overall_sd;
 if(key==="offense_sd")return row.ratings.offense_sd;
 if(key==="defense_sd")return row.ratings.defense_sd;
 return row.metrics[key];
}
function buildUI(){
 const seasons=Object.entries(data.seasons).sort((a,b)=>Number(b[0])-Number(a[0]));

 app.innerHTML='<p class="eyebrow">BETWISE NBA · LIVE DATA</p><h1 id="rank-page-title"></h1><p class="page-intro">Rank all 30 NBA teams by completed regular-season performance. Ratings use raw offensive and defensive output without opponent-strength adjustments.</p><div class="nba-rank-season-control"><label for="nba-rank-season">Choose season<select id="nba-rank-season" aria-label="Select NBA season"></select></label></div><div class="rank-hero"><img src="https://matchlab.parlaycalculator.bet/nba/dashboard/hero-new.png?v=nba-giannis7-20261016" alt="NBA players featured on the BetWise NBA Dashboard"></div><p class="rank-tabs-label">Explore NBA Rankings</p><nav class="rank-tabs" aria-label="NBA rankings"><a href="/nba/rankings/"'+(mode==="overall"?' class="active" aria-current="page"':"")+'><span>Overall Team Rankings</span></a><a href="/nba/offensive-rankings/"'+(mode==="offense"?' class="active" aria-current="page"':"")+'><span>Offensive Rankings</span></a><a href="/nba/defensive-rankings/"'+(mode==="defense"?' class="active" aria-current="page"':"")+'><span>Defensive Rankings</span></a></nav><div class="data-table-wrap"><div class="nba-rank-table-scroll" id="rank-table-scroll"><table class="nba-rank-table"><thead id="rank-table-head"></thead><tbody id="rank-table-body"></tbody></table></div></div><p class="nba-rank-source">Source: <a id="rank-source" target="_blank" rel="noopener noreferrer">Basketball-Reference NBA team season tables</a>. Offensive rating is points per 100 estimated possessions; defensive rating is points allowed per 100 estimated possessions. Ratings show each team’s difference from that season’s league average. Positive defensive rating means better-than-average defense. Standard deviation is shown separately. This describes season performance, not a prediction or betting recommendation.</p>';
 let activeColumn="rank",activeAscending=true;
 const seasonSelect=app.querySelector("#nba-rank-season");
 const requestedSeason=new URLSearchParams(location.search).get("season");
 selectedYear=seasons.some(([year])=>year===requestedSeason)?requestedSeason:seasons[0][0];
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
 function syncTopScrollbar(){
  const wrapper=app.querySelector("#rank-table-scroll"),table=app.querySelector(".nba-rank-table"),bar=app.querySelector(".nba-rank-table-scrubber"),thumb=bar?.querySelector(".nba-rank-table-thumb");
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
   wrapper.addEventListener("scroll",()=>{const current=app.querySelector(".nba-rank-table-scrubber");if(current){const currentTable=app.querySelector(".nba-rank-table");if(currentTable){const currentThumb=current.querySelector(".nba-rank-table-thumb"),maxScroll=Math.max(0,currentTable.scrollWidth-wrapper.clientWidth),trackWidth=current.clientWidth||wrapper.clientWidth,thumbWidth=maxScroll?Math.min(trackWidth,Math.max(44,trackWidth*wrapper.clientWidth/currentTable.scrollWidth)):trackWidth,maxThumb=Math.max(0,trackWidth-thumbWidth);currentThumb.style.width=thumbWidth+"px";currentThumb.style.transform="translateX("+(maxScroll?(wrapper.scrollLeft/maxScroll)*maxThumb:0)+"px)";current.setAttribute("aria-valuenow",String(Math.round(wrapper.scrollLeft)))}}});
   window.addEventListener("resize",()=>{const current=app.querySelector(".nba-rank-table-scrubber");if(current){const currentTable=app.querySelector(".nba-rank-table");if(currentTable){const currentThumb=current.querySelector(".nba-rank-table-thumb"),maxScroll=Math.max(0,currentTable.scrollWidth-wrapper.clientWidth),trackWidth=current.clientWidth||wrapper.clientWidth,thumbWidth=maxScroll?Math.min(trackWidth,Math.max(44,trackWidth*wrapper.clientWidth/currentTable.scrollWidth)):trackWidth,maxThumb=Math.max(0,trackWidth-thumbWidth);currentThumb.style.width=thumbWidth+"px";currentThumb.style.transform="translateX("+(maxScroll?(wrapper.scrollLeft/maxScroll)*maxThumb:0)+"px)";current.setAttribute("aria-valuemax",String(Math.round(maxScroll)));current.setAttribute("aria-valuenow",String(Math.round(wrapper.scrollLeft)))}}});
  }
  if(!bar.dataset.dragReady){
   bar.dataset.dragReady="true";
   let dragging=false,dragOffset=0;
   const setFromPointer=(clientX)=>{
    const rect=bar.getBoundingClientRect(),trackWidth=bar.clientWidth||rect.width,tableNow=app.querySelector(".nba-rank-table"),maxScroll=Math.max(0,tableNow.scrollWidth-wrapper.clientWidth),thumbWidth=thumb.offsetWidth,maxThumb=Math.max(0,trackWidth-thumbWidth);
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
  rows=rows.map(row=>({...row,page_rank:Number(row.ranks[modelRankKey])}));
  function valueFor(row,key){
   if(key==="team")return row.team;
   if(key==="rank")return Number(row.page_rank);
   if(key==="record"){const m=String(row.record||"").match(/(\d+)\s*[-–]\s*(\d+)/);return m?Number(m[1])/(Number(m[1])+Number(m[2])||1):null}
   return num(ratingValue(row,key));
  }
  rows.sort((a,b)=>{const av=valueFor(a,activeColumn),bv=valueFor(b,activeColumn);if(typeof av==="string"&&typeof bv==="string"){const c=av.localeCompare(bv);return activeAscending?c:-c}if(av===null&&bv!==null)return 1;if(bv===null&&av!==null)return -1;if(av!==bv)return activeAscending?av-bv:bv-av;return a.team.localeCompare(b.team)});
  app.querySelector("#rank-page-title").textContent=season.label+" NBA "+names[mode];
  app.querySelector("#rank-source").href=season.source_url;
  const cols=[{key:"rank",label:"Rank"},{key:"team",label:"Team"},{key:"record",label:"Record"}];
  const keys=visible[mode]||visible.overall;
  keys.forEach(k=>cols.push({key:k,label:pretty(k)}));
  cols.forEach(c=>c.help=metricHelp[c.key]||("Selected-season "+pretty(c.key)+" value for this team."));
  app.querySelector("#rank-table-head").innerHTML='<tr>'+cols.map(c=>'<th scope="col" aria-sort="'+(activeColumn===c.key?(activeAscending?"ascending":"descending"):"none")+'"><div class="nba-th-content"><button type="button" class="nba-sort-button" data-sort-key="'+h(c.key)+'" aria-label="Sort by '+h(c.label)+'">'+h(c.label)+' <span class="nba-sort-arrow" aria-hidden="true">'+(activeColumn===c.key?(activeAscending?"↑":"↓"):"↕")+'</span></button><span class="help-wrap"><button class="help-btn" type="button" aria-label="About '+h(c.label)+'" aria-expanded="false">?</button><span class="help-pop" role="tooltip">'+h(c.help)+'</span></span></div></th>').join("")+'</tr><tr class="nba-scrollbar-row"><th class="nba-scrollbar-cell" colspan="'+cols.length+'"><div class="nba-rank-table-scrubber" role="scrollbar" aria-label="Scroll ranking table horizontally" aria-controls="rank-table-scroll" aria-orientation="horizontal" aria-valuemin="0" aria-valuemax="0" aria-valuenow="0" tabindex="0"><span class="nba-rank-table-thumb" aria-hidden="true"></span></div></th></tr>';
  app.querySelectorAll("#rank-table-head [data-sort-key]").forEach(button=>button.addEventListener("click",()=>{const key=button.dataset.sortKey;if(activeColumn===key)activeAscending=!activeAscending;else{activeColumn=key;activeAscending=key==="team"||key==="record"||key==="rank"?true:!(data.lower_is_better||[]).includes(key)}render()}));
  app.querySelector("#rank-table-body").innerHTML=rows.map(row=>"<tr>"+cols.map(col=>{
   if(col.key==="rank")return "<td>"+row.page_rank+"</td>";
   if(col.key==="team")return '<td><a class="nba-rank-team" href="/nba/teams/'+h(row.slug)+'/"><img loading="lazy" src="'+h(row.logo)+'" alt=""><span>'+h(row.team)+'</span></a></td>';
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
fetch("/nba/rankings/data/nba-team-rankings.json?v=1",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("NBA ranking archive is not available");return r.json()}).then(d=>{data=d;buildUI()}).catch(()=>{app.innerHTML='<div class="nba-rankings-error"><h1>'+h(names[mode])+'</h1><p>Ranking data is temporarily unavailable. Please refresh shortly.</p></div>'});
})();