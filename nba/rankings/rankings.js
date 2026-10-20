(()=>{"use strict";
const app=document.querySelector("#nba-rankings-app");
if(!app)return;
const mode=app.dataset.rankingsMode||"overall";
const names={overall:"Overall Team Rankings",offense:"Offensive Rankings",defense:"Defensive Rankings"};
const modelRankKey={overall:"overall",offense:"offense",defense:"defense"}[mode]||"overall";
const metricKeys={};
const h=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pctKeys=new Set(["fg_pct","opp_fg_pct","three_pct","opp_three_pct","offensive_rebound_rate","defensive_rebound_rate","efg_pct","opp_efg_pct","ts_pct","ft_pct","three_attempt_rate","ft_rate","ft_made_rate","tov_pct","opp_tov_pct","rim_fg_pct","opp_rim_fg_pct"]);
const signedKeys=new Set(["turnover_margin","overall_rating","offense_rating","defense_rating","net_rating"]);
const ratingKeys=new Set(["overall_rating","offense_rating","defense_rating","ortg","drtg","net_rating"]);
const visible={
overall:["overall_rating","overall_sd","offense_rating","defense_rating","ortg","drtg","net_rating","pace","ppg","ppg_allowed"],
offense:["offense_rating","offense_sd","ortg","ppg_home","ppg_away","fg_pct","three_pct","assists_per_game","turnovers_per_game","offensive_rebound_rate","pace"],
defense:["defense_rating","defense_sd","drtg","ppg_allowed","opp_fg_pct","opp_three_pct","rebounds_allowed_per_game","opp_efg_pct","opponent_turnovers_per_game","steals_per_game","blocks_per_game","turnover_margin"]
};
const directions={};
let data=null,selectedYear=null;
function pretty(k){return data.metric_labels[k]||k.replace(/_/g," ").replace(/\b\w/g,x=>x.toUpperCase())}
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
function metricSelect(selected){
 return Object.keys(data.metric_labels).map(k=>'<option value="'+h(k)+'"'+(k===selected?" selected":"")+'>'+h(pretty(k))+'</option>').join("");
}
function buildUI(){
 const seasons=Object.entries(data.seasons).sort((a,b)=>Number(b[0])-Number(a[0]));
 selectedYear=seasons[0][0];
 app.innerHTML='<section class="nba-rankings-hero"><p class="rank-kicker">BETWISE · NBA TEAM ANALYTICS</p><h1>'+h(names[mode])+'</h1><p>Rank all 30 NBA teams by season performance. Efficiency ratings use raw offensive and defensive output, with no opponent-strength adjustment.</p><div class="rank-nav"><a href="/nba/rankings/"'+(mode==="overall"?' aria-current="page"':"")+'>Overall Team Rankings</a><a href="/nba/offensive-rankings/"'+(mode==="offense"?' aria-current="page"':"")+'>Offensive Rankings</a><a href="/nba/defensive-rankings/"'+(mode==="defense"?' aria-current="page"':"")+'>Defensive Rankings</a><a href="/nba/teams/">NBA Team Pages</a></div></section><section class="nba-rank-controls" aria-label="Ranking controls"><label>Season<select id="rank-season">'+seasons.map(([y,s])=>'<option value="'+h(y)+'">'+h(s.label)+'</option>').join("")+'</select></label><label>Conference<select id="rank-conference"><option value="">All conferences</option><option>Eastern</option><option>Western</option></select></label><label class="rank-search">Search team<input id="rank-search" type="search" placeholder="Team name"></label><label>Rank by<select id="rank-sort">'+metricSelect(mode==="overall"?"overall_rating":mode==="offense"?"offense_rating":"defense_rating")+'</select></label><button type="button" id="rank-reset">Reset filters</button></section><section class="nba-metric-filter-panel"><div class="metric-filter-heading"><div><p class="rank-kicker">ADVANCED FILTERS</p><h2>Filter teams by metrics</h2></div><button type="button" id="rank-add-filter">+ Add metric filter</button></div><p>Set one or more minimum and maximum values. All added filters apply together.</p><div id="rank-filter-list"></div></section><section class="nba-rank-summary" id="rank-summary"></section><section class="nba-rank-table-section"><div class="nba-rank-table-heading"><div><p class="rank-kicker">'+h(names[mode].toUpperCase())+'</p><h2 id="rank-season-heading"></h2></div><span id="rank-result-count"></span></div><div class="nba-rank-table-scroll"><table class="nba-rank-table"><thead id="rank-table-head"></thead><tbody id="rank-table-body"></tbody></table></div></section><p class="nba-rank-source">Source: <a id="rank-source" target="_blank" rel="noopener noreferrer">Basketball-Reference NBA team season tables</a>. Offensive rating is points per 100 estimated possessions; defensive rating is points allowed per 100 estimated possessions. Ratings show the team’s difference from that season’s league average. A positive defensive rating means better-than-average defense. Standard deviation is shown separately. This is season performance context, not a prediction or betting recommendation.</p>';
 const yearSelect=app.querySelector("#rank-season");
 const conf=app.querySelector("#rank-conference");
 const search=app.querySelector("#rank-search");
 const sort=app.querySelector("#rank-sort");
 const filters=app.querySelector("#rank-filter-list");
 function addFilter(){
  const row=document.createElement("div");row.className="nba-metric-filter";
  const select=document.createElement("select");select.setAttribute("aria-label","Metric");
  select.innerHTML=metricSelect("ppg");
  const min=document.createElement("input");min.type="number";min.step="any";min.placeholder="Minimum";min.setAttribute("aria-label","Minimum value");
  const max=document.createElement("input");max.type="number";max.step="any";max.placeholder="Maximum";max.setAttribute("aria-label","Maximum value");
  const remove=document.createElement("button");remove.type="button";remove.className="filter-remove";remove.textContent="Remove";remove.addEventListener("click",()=>{row.remove();render()});
  [select,min,max].forEach(el=>el.addEventListener("input",render));
  row.append(select,min,max,remove);filters.appendChild(row);render();
 }
 function metricOptions(){
  return Object.keys(data.metric_labels).map(k=>({key:k,label:pretty(k)}));
 }
 function render(){
  const season=data.seasons[yearSelect.value];if(!season)return;
  const sortKey=sort.value;
  const minMax=[...filters.querySelectorAll(".nba-metric-filter")].map(row=>({key:row.querySelector("select").value,min:num(row.querySelectorAll("input")[0].value),max:num(row.querySelectorAll("input")[1].value)}));
  let rows=season.teams.filter(row=>{
   if(conf.value&&row.conference!==conf.value)return false;
   if(search.value&&!row.team.toLowerCase().includes(search.value.trim().toLowerCase()))return false;
   for(const f of minMax){const v=num(ratingValue(row,f.key));if(v===null)return false;if(f.min!==null&&v<f.min)return false;if(f.max!==null&&v>f.max)return false}
   return true;
  });
  const lower=(data.lower_is_better||[]).includes(sortKey);
  rows.sort((a,b)=>{
   const av=num(ratingValue(a,sortKey)),bv=num(ratingValue(b,sortKey));
   if(av===null&&bv!==null)return 1;if(bv===null&&av!==null)return -1;if(av!==bv)return lower?av-bv:bv-av;
   return a.team.localeCompare(b.team);
  });
  let rank=0,last=null;
  const ranked=rows.map((row,i)=>{const val=num(ratingValue(row,sortKey));const tie=val===null?"missing":Number(val).toFixed(8);if(i===0||tie!==last)rank=i+1;last=tie;return {...row,selected_rank:rank}});
  const primary=ranked[0];
  const overallTop=season.teams.slice().sort((a,b)=>a.ranks.overall-b.ranks.overall)[0];
  const offTop=season.teams.slice().sort((a,b)=>a.ranks.offense-b.ranks.offense)[0];
  const defTop=season.teams.slice().sort((a,b)=>a.ranks.defense-b.ranks.defense)[0];
  app.querySelector("#rank-summary").innerHTML='<article><span>Teams shown</span><strong>'+ranked.length+' / 30</strong></article><article><span>Overall #1</span><strong>'+h(overallTop.team)+'</strong><small>'+fmt(overallTop.metrics.overall_rating,"overall_rating")+' pts/100 vs avg</small></article><article><span>Best offense</span><strong>'+h(offTop.team)+'</strong><small>'+fmt(offTop.metrics.offense_rating,"offense_rating")+' pts/100 vs avg</small></article><article><span>Best defense</span><strong>'+h(defTop.team)+'</strong><small>'+fmt(defTop.metrics.defense_rating,"defense_rating")+' pts/100 vs avg</small></article>';
  app.querySelector("#rank-season-heading").textContent=season.label+" · "+pretty(sortKey);
  app.querySelector("#rank-result-count").textContent=ranked.length+" teams";
  app.querySelector("#rank-source").href=season.source_url;
  const cols=[{key:"selected_rank",label:"Rank"},{key:"team",label:"Team"},{key:"record",label:"Record"},{key:"model_rank",label:mode==="overall"?"Overall #":mode==="offense"?"Offense #":"Defense #"}];
  const keys=visible[mode]||visible.overall;
  keys.forEach(k=>{if(k!=="overall_rating"&&k!=="offense_rating"&&k!=="defense_rating"&&k!=="overall_sd"&&k!=="offense_sd"&&k!=="defense_sd"&&!keys.includes(sortKey)){}});
  const displayed=new Set(keys);
  if(!displayed.has(sortKey)&&sortKey!=="team")cols.push({key:sortKey,label:pretty(sortKey)});
  keys.forEach(k=>cols.push({key:k,label:k.endsWith("_sd")?"SD":pretty(k)}));
  app.querySelector("#rank-table-head").innerHTML="<tr>"+cols.map(c=>"<th>"+h(c.label)+"</th>").join("")+"</tr>";
  app.querySelector("#rank-table-body").innerHTML=ranked.map(row=>"<tr>"+cols.map(col=>{
   if(col.key==="selected_rank")return "<td>"+row.selected_rank+"</td>";
   if(col.key==="team")return '<td><a class="nba-rank-team" href="/nba/teams/'+h(row.slug)+'/"><img loading="lazy" src="'+h(row.logo)+'" alt=""><span>'+h(row.team)+'</span></a></td>';
   if(col.key==="record")return "<td>"+h(row.record||"—")+"</td>";
   if(col.key==="model_rank")return "<td>"+h(row.ranks[modelRankKey])+"</td>";
   const value=ratingValue(row,col.key);
   return "<td>"+h(fmt(value,col.key))+"</td>";
  }).join("")+"</tr>").join("")||'<tr><td colspan="'+cols.length+'">No teams match these filters.</td></tr>';
 }
 yearSelect.addEventListener("change",render);conf.addEventListener("change",render);search.addEventListener("input",render);sort.addEventListener("change",render);
 app.querySelector("#rank-add-filter").addEventListener("click",addFilter);
 app.querySelector("#rank-reset").addEventListener("click",()=>{conf.value="";search.value="";sort.value=mode==="overall"?"overall_rating":mode==="offense"?"offense_rating":"defense_rating";filters.innerHTML="";render()});
 addFilter();
}
fetch("/nba/rankings/data/nba-team-rankings.json?v=1",{cache:"no-store"}).then(r=>{if(!r.ok)throw new Error("NBA ranking archive is not available");return r.json()}).then(d=>{data=d;buildUI()}).catch(()=>{app.innerHTML='<div class="nba-rankings-error"><h1>'+h(names[mode])+'</h1><p>Ranking data is temporarily unavailable. Please refresh shortly.</p></div>'});
})();