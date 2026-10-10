(()=>{'use strict';
const match=location.pathname.match(/^\/(mlb|cbb)\/teams\/([^/]+)\/?$/);
if(!match)return;
const sport=match[1],main=document.querySelector('main.research-main'),seed=document.querySelector('#team-season-data');
if(!main||!seed)return;
let data;try{data=JSON.parse(seed.textContent)}catch{return}
const heading=main.querySelector('.team-research-heading'),breadcrumb=main.querySelector('.research-breadcrumbs');
if(!heading)return;
const teamName=heading.querySelector('h1')?.textContent?.trim()||match[2],logo=heading.querySelector('img')?.getAttribute('src')||'',subtitle=heading.querySelector('div>p:last-child')?.textContent||'';
const seasons=Array.isArray(data.seasons)?data.seasons:[],current=seasons.at(-1)?.key||'2026';
const conf=sport==='mlb'?['Runs / Game','Batting Average','On-Base %','Slugging %','Home Runs','Strikeout Rate','ERA','WHIP','Runs Allowed / Game','Opponent Average','Bullpen ERA','Strikeouts / 9']:['Points / Game','Offensive Rating','Effective FG %','3P %','Free Throw %','Turnover Rate','Points Allowed / Game','Defensive Rating','Opponent eFG %','Rebound Rate','Steals / Game','Blocks / Game'];
const source=data.seasons||[];const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const sportTitle=sport==='mlb'?'MLB':'CBB',route='/'+sport+'/teams/';
const section=(id,kicker,title,inside)=>'<section id="'+id+'" class="wise-team-section"><div class="wise-team-head"><p>'+kicker+'</p><h2>'+title+'</h2></div>'+inside+'</section>';
const empty=message=>'<div class="wise-empty">'+message+'</div>';
const order=sport==='cbb'?['snapshot','coaches','recruiting','schedule','metrics','players','accolades']:['snapshot','coaches','draft','schedule','metrics','players','accolades'];
const nav=order.map(id=>'<a href="#'+id+'">'+({snapshot:'Season Snapshot',metrics:'Advanced Metrics',schedule:'Schedule',players:'Player Stats',coaches:'Coaches',recruiting:'Recruiting Classes',draft:'Draft Class',accolades:sport==='cbb'?'Program Accolades':'Franchise Accolades'}[id])+'</a>').join('');
document.body.classList.add(sport==='cbb'?'wise-cfb-template':'wise-nba-template');
main.classList.add('wise-team-main');
main.innerHTML='<div class="wise-team-hero"><div class="wise-team-logo"><img src="'+esc(logo)+'" alt="'+esc(teamName)+' logo"></div><div class="wise-team-hero-copy"><p class="wise-eyebrow">'+sportTitle+' TEAM RESEARCH</p><h1>'+esc(teamName)+'</h1><p>'+esc(subtitle)+'</p><div class="wise-hero-season"><label for="wiseSeasonSelect">Season</label><select id="wiseSeasonSelect">'+seasons.slice().reverse().map(y=>'<option value="'+esc(y.key)+'">'+esc(y.label)+'</option>').join('')+'</select></div></div></div><nav class="wise-team-tabs" aria-label="Team page sections">'+nav+'</nav><div id="wiseTeamContents"></div>';
function renderMlbHonors(team){
if(!team)return empty('Franchise honors are being verified.');
const categories=[['World Series Championships',team.team?.world_series],['League Pennants',team.team?.league_pennants],['Division Titles',team.team?.division_titles]];
const rows=categories.map(([label,item])=>{const ready=item?.count!==null&&item?.count!==undefined;
return '<article class="wise-honor-card"><span>'+esc(label)+'</span><strong>'+ (ready?esc(item.count):'—') +'</strong><small>'+(ready&&item.years?.length?esc(item.years.join(' · ')):'Historical record pending verification')+'</small></article>'}).join('');
const awards=[['MVP','mvp'],['Cy Young','cy_young'],['Rookie of the Year','rookie_of_the_year'],['Gold Gloves','gold_glove'],['Silver Sluggers','silver_slugger']];
const players=awards.map(([name,key])=>{const entries=mlbAwards?.awards?.[match[2]]?.[key];const available=Array.isArray(entries);return '<article class="wise-honor-card"><span>'+esc(name)+'</span><strong>'+(available?esc(entries.length):'—')+'</strong><small>'+(available?(entries.length?esc(entries.slice(-3).map(x=>x.player+' ('+x.year+')').join(' · ')):'No entries in imported records'):'Historical winners pending verification')+'</small></article>'}).join('');
return '<div class="wise-honor-heading">TEAM</div><div class="wise-honors-grid">'+rows+'</div><div class="wise-honor-heading">PLAYER</div><div class="wise-honors-grid">'+players+'</div><p class="wise-honor-note">All-time franchise history includes former team names and cities. Award data is preliminary and subject to franchise attribution review. Missing categories remain blank; they are not zero.</p>';
}
const select=main.querySelector('#wiseSeasonSelect'),container=main.querySelector('#wiseTeamContents');
let mlbSnapshots=null;
let mlbAccolades=null;
let mlbAwards=null;

select.value=current;
function render(){const y=seasons.find(x=>String(x.key)===select.value)||{};const label=y.label||select.value;const mlbRow=sport==='mlb'?mlbSnapshots?.seasons?.[String(select.value)]?.[match[2]]:null;const record=mlbRow?.games_played?{wins:mlbRow.wins,losses:mlbRow.losses}:y.record;
const summary=[['Record',record&&typeof record==='object'?[record.wins,record.losses].join('–'):record],sport==='mlb'?['Runs / Game',mlbRow?.runs_per_game]:['Points / Game',null],sport==='mlb'?['Runs Allowed / Game',mlbRow?.runs_allowed_per_game]:['Points Allowed / Game',null],['Home Record',mlbRow?.games_played?mlbRow.home.wins+'–'+mlbRow.home.losses:null],['Road Record',mlbRow?.games_played?mlbRow.away.wins+'–'+mlbRow.away.losses:null],['ATS Record',null],['O/U Record',null]].map(([k,v])=>'<article class="wise-stat"><strong>'+esc(v||'—')+'</strong><span>'+k+'</span></article>').join('');
const metrics=conf.map((k,i)=>'<article class="wise-metric"><span>'+esc(k)+'</span><strong>—</strong><small>Data pending</small></article>').join('');
const metricTile=label=>'<article class="wise-metric"><span>'+esc(label)+'</span><strong>—</strong><small>Data pending</small></article>';
const mlbMetrics='<div class="wise-stat-split"><div><h3>HITTING</h3><div class="wise-metrics">'+conf.slice(0,6).map(metricTile).join('')+'</div></div><div><h3>PITCHING</h3><div class="wise-metrics">'+conf.slice(6).map(metricTile).join('')+'</div></div></div>';
const games=Array.isArray(y.games)?y.games:[];
const schedule=games.length?'<div class="wise-scroll"><table><thead><tr><th>Date</th><th>Opponent</th><th>Result</th><th>Score</th></tr></thead><tbody>'+games.slice(0,12).map(g=>'<tr><td>'+esc(g.date)+'</td><td>'+esc(g.opponent_name||g.opponent)+'</td><td>'+esc(g.result)+'</td><td>'+esc(g.score)+'</td></tr>').join('')+'</tbody></table></div>'+ (games.length>12?'<button type="button" id="wiseMoreGames">Show all '+games.length+' games</button>':''):empty('Season schedule not populated yet.');
container.innerHTML=section('snapshot','SEASON SNAPSHOT',esc(teamName)+' · '+esc(label),'<div class="wise-snapshot-grid">'+summary+'</div>')+section('coaches','COACHING STAFF',sport==='mlb'?'Manager & Coaching Staff':'Head Coach',empty('Coaching history has not been populated yet.'))+(sport==='cbb'?section('recruiting','RECRUITING CLASSES','Recruiting Class · '+esc(label),empty('Recruiting class rankings and commitments have not been populated yet.')):section('draft','DRAFT CLASS','MLB Draft Class',empty('Draft history has not been populated yet.')))+section('schedule','SCHEDULE & RESULTS','Season schedule',schedule)+section('metrics','ADVANCED METRICS',sport==='mlb'?'Hitting & Pitching':'Offense & Defense',sport==='mlb'?mlbMetrics:'<div class="wise-metrics">'+metrics+'</div>')+section('players','PLAYER STATISTICS','Season leaders & roster',empty('Player statistics will appear when verified season data is added.'))+section('accolades',sport==='mlb'?'FRANCHISE HISTORY':'PROGRAM ACCOLADES',sport==='mlb'?'Franchise Accolades':'Program Accolades',sport==='cbb'?'<div class="wise-program-history">'+empty('Championships, conference titles and major player awards have not been populated yet.')+'<details class="wise-draft-history"><summary>NBA First-Round Draft Picks <span aria-hidden="true">+</span></summary>'+empty('Historical first-round NBA draft selections for this program have not been populated yet.')+'</details></div>':renderMlbHonors(mlbAccolades?.teams?.[match[2]]));
const more=container.querySelector('#wiseMoreGames');if(more)more.addEventListener('click',()=>{const tbody=container.querySelector('#schedule tbody');tbody.innerHTML=games.map(g=>'<tr><td>'+esc(g.date)+'</td><td>'+esc(g.opponent_name||g.opponent)+'</td><td>'+esc(g.result)+'</td><td>'+esc(g.score)+'</td></tr>').join('');more.remove()});
}
select.addEventListener('change',render);render();
if(sport==='mlb')fetch('/data/mlb/award-winners.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('Historical MLB awards unavailable');return r.json()}).then(d=>{mlbAwards=d;render()}).catch(()=>{});
if(sport==='mlb')fetch('/data/mlb/franchise-accolades.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('No franchise awards data');return r.json()}).then(d=>{mlbAccolades=d;render()}).catch(()=>{});
if(sport==='mlb')fetch('/data/mlb/season-snapshots.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('No MLB season data');return r.json()}).then(d=>{mlbSnapshots=d;render()}).catch(()=>{});
})();