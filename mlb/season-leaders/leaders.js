(()=>{'use strict';
const app=document.querySelector('#mlb-leaders-app');if(!app)return;
const h=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cols={hitting:[['gamesPlayed','G'],['plateAppearances','PA'],['atBats','AB'],['runs','R'],['hits','H'],['doubles','2B'],['triples','3B'],['homeRuns','HR'],['rbi','RBI'],['stolenBases','SB'],['baseOnBalls','BB'],['strikeOuts','K'],['avg','AVG'],['obp','OBP'],['slg','SLG'],['ops','OPS']],pitching:[['gamesPlayed','G'],['gamesStarted','GS'],['wins','W'],['losses','L'],['saves','SV'],['holds','HLD'],['inningsPitched','IP'],['strikeOuts','K'],['baseOnBalls','BB'],['hits','H'],['era','ERA'],['whip','WHIP'],['strikeoutsPer9Inn','K/9']]};
const rates=new Set(['avg','obp','slg','ops','era','whip','strikeoutsPer9Inn']);
const low=new Set(['era','whip','losses','baseOnBalls','hits']);
const categories={hitting:[['homeRuns','Home Runs'],['rbi','Runs Batted In'],['hits','Hits'],['runs','Runs'],['stolenBases','Stolen Bases'],['avg','Batting Average'],['obp','On-Base Percentage'],['ops','OPS']],pitching:[['wins','Wins'],['strikeOuts','Strikeouts'],['saves','Saves'],['holds','Holds'],['era','ERA'],['whip','WHIP'],['strikeoutsPer9Inn','Strikeouts / 9']]};
let data,years,group='hitting',sort='homeRuns',asc=false,request=0;
function fmt(v,k){if(v===null||v===undefined)return '—';if(k==='inningsPitched')return h(v);if(['avg','obp','slg','ops'].includes(k))return Number(v).toFixed(3).replace(/^0/,'');if(rates.has(k))return Number(v).toFixed(2);return String(Math.round(v));}
function value(r,k){return k==='inningsPitched'?r.stats.outs:k==='name'||k==='team'?r[k]:r.stats[k];}
function ordered(rows,key,ascending){return rows.slice().sort((a,b)=>{const x=value(a,key),y=value(b,key);if(x==null&&y!=null)return 1;if(y==null&&x!=null)return -1;const n=typeof x==='string'?x.localeCompare(y):x-y;return (ascending?n:-n)||a.name.localeCompare(b.name);});}
function qualified(r,key){if(!rates.has(key))return true;return group==='hitting'?r.stats.plateAppearances>=data.min_pa:r.stats.outs>=data.min_outs;}
function player(r){return '<a href="https://www.mlb.com/player/'+h(r.id)+'" target="_blank" rel="noopener noreferrer">'+h(r.name)+'</a>';}
function render(){
 if(!data)return;
 app.querySelector('h1').textContent=data.season+' MLB Season Leaders';
 app.querySelector('#leader-status').textContent='Regular season only · Updated '+new Date(data.updated_at).toLocaleString('en-US',{timeZone:'America/New_York',dateStyle:'medium',timeStyle:'short'})+' ET';
 app.querySelector('#leader-note').textContent=data.qualification_note+' Batting rate minimum: '+data.min_pa+' PA. Pitching rate minimum: '+(data.min_outs/3)+' IP.';
 app.querySelector('#leader-source').href=data.source_url;
 app.querySelectorAll('[data-group]').forEach(b=>{b.classList.toggle('active',b.dataset.group===group);b.setAttribute('aria-pressed',String(b.dataset.group===group));});
 const query=app.querySelector('#player-search').value.trim().toLowerCase(),team=app.querySelector('#player-team').value;
 const rows=data[group].filter(r=>(!team||r.team===team)&&(!query||(r.name+' '+r.team).toLowerCase().includes(query)));
 app.querySelector('#leader-cards').innerHTML=categories[group].map(([key,label])=>{
  const leaders=ordered(rows.filter(r=>r.stats[key]!=null&&qualified(r,key)&&(rates.has(key)||r.stats[key]>0)),key,group==='pitching'&&low.has(key)).slice(0,10);
  let rank=0,previous;
  return '<section class="leader-card"><h3>'+h(label)+'</h3><p>'+(rates.has(key)?'Qualified players':'Season totals')+'</p><div class="leader-scroll"><table><thead><tr><th>Rank</th><th>Player</th><th>Team</th><th>'+h(label)+'</th></tr></thead><tbody>'+leaders.map((r,i)=>{const v=r.stats[key];if(v!==previous)rank=i+1;previous=v;return '<tr><td>'+rank+'</td><td>'+player(r)+'</td><td>'+h(r.team)+'</td><td>'+fmt(v,key)+'</td></tr>';}).join('')+(leaders.length?'':'<tr><td colspan="4">No eligible players.</td></tr>')+'</tbody></table></div></section>';
 }).join('');
 const filtered=app.querySelector('#qualified-only').checked?rows.filter(r=>qualified(r,group==='hitting'?'ops':'era')):rows;
 const tableCols=[['name','Player'],['team','Team'],...cols[group]];
 app.querySelector('#player-head').innerHTML='<tr>'+tableCols.map(([key,label])=>'<th scope="col" aria-sort="'+(sort===key?(asc?'ascending':'descending'):'none')+'"><button data-sort="'+key+'">'+h(label)+' '+(sort===key?(asc?'↑':'↓'):'↕')+'</button></th>').join('')+'</tr>';
 app.querySelector('#player-body').innerHTML=ordered(filtered,sort,asc).map(r=>'<tr>'+tableCols.map(([key])=>'<td>'+(key==='name'?player(r):key==='team'?h(r.team):fmt(r.stats[key],key))+'</td>').join('')+'</tr>').join('')||'<tr><td colspan="20">No matching players.</td></tr>';
 app.querySelector('#player-count').textContent=filtered.length+' players · Select a column to sort';
 app.querySelectorAll('[data-sort]').forEach(b=>b.addEventListener('click',()=>{const key=b.dataset.sort;if(sort===key)asc=!asc;else{sort=key;asc=key==='name'||key==='team'||group==='pitching'&&low.has(key);}render();}));
}
async function load(year){const token=++request;app.querySelector('#leader-status').textContent='Loading player statistics…';try{const response=await fetch('/mlb/season-leaders/data/'+year+'.json',{cache:'no-store'});if(!response.ok)throw Error();const next=await response.json();if(token!==request)return;data=next;app.querySelector('#player-team').innerHTML='<option value="">All teams</option>'+[...new Set([...data.hitting,...data.pitching].map(r=>r.team))].sort().map(t=>'<option>'+h(t)+'</option>').join('');render();}catch(e){if(token===request){data=null;app.querySelector('#leader-status').textContent='Player statistics are temporarily unavailable. Please refresh shortly.';app.querySelector('#leader-cards').innerHTML='';app.querySelector('#player-body').innerHTML='';}}}
fetch('/mlb/season-leaders/data/seasons.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error();return r.json();}).then(async list=>{
 years=list.sort((a,b)=>b-a);const year=Number(new URLSearchParams(location.search).get('season'));const selected=years.includes(year)?year:years[0];
 app.querySelector('#leader-season').innerHTML=years.map(y=>'<option>'+y+'</option>').join('');app.querySelector('#leader-season').value=selected;
 app.querySelector('#leader-season').addEventListener('change',e=>{const u=new URL(location.href);u.searchParams.set('season',e.target.value);history.replaceState(null,'',u);load(e.target.value);});
 app.querySelectorAll('[data-group]').forEach(b=>b.addEventListener('click',()=>{group=b.dataset.group;sort=group==='hitting'?'homeRuns':'strikeOuts';asc=false;render();}));
 ['player-search','player-team','qualified-only'].forEach(id=>app.querySelector('#'+id).addEventListener(id==='player-search'?'input':'change',render));
 await load(selected);
}).catch(()=>{app.querySelector('#leader-status').textContent='Season list is temporarily unavailable. Please refresh shortly.';});
})();
