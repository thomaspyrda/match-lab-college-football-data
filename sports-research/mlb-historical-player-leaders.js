(()=>{'use strict';
if(!/^\/mlb\/teams\/[^/]+\/?$/.test(location.pathname))return;
const slug=location.pathname.split('/').filter(Boolean).at(-1);
const safe=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const headers={
 hitters:[['name','Player'],['ab','AB'],['h','H'],['hr','HR'],['rbi','RBI'],['avg','AVG'],['obp','OBP'],['ops','OPS']],
 starters:[['name','Pitcher'],['gs','GS'],['ip','IP'],['w','W'],['l','L'],['era','ERA'],['whip','WHIP'],['so','SO']],
 relievers:[['name','Pitcher'],['gp','G'],['gs','GS'],['sv','SV'],['ip','IP'],['era','ERA'],['whip','WHIP'],['so','SO']]
};
const table=(label,rows,columns)=>'<h3>'+safe(label)+'</h3><div class="wise-scroll"><table><thead><tr>'+columns.map(x=>'<th scope="col">'+safe(x[1])+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+columns.map(([k])=>'<td>'+safe(r[k])+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
let dataset=null, last='', loading=false;
function paint(){
 const section=document.querySelector('#players'),selector=document.querySelector('#wiseSeasonSelect');
 if(!section||!selector||!dataset)return;
 const year=String(selector.value),record=dataset.years?.[year];
 const key=slug+':'+year;
 if(section.dataset.historicalPlayers===key)return;
 const body=section.querySelector('.wise-empty');
 if(!record || !body) return;
 const markup='<p class="wise-player-source">Team-specific regular-season statistics · '+safe(year)+' · Top 20 hitters by at-bats; top five starters and relievers.</p>'+
 table('Hitters',record.hitters,headers.hitters)+table('Starting pitchers',record.starters,headers.starters)+table('Relief pitchers',record.relievers,headers.relievers);
 body.outerHTML='<div class="wise-historical-players">'+markup+'</div>';
 section.dataset.historicalPlayers=key;
}
const observer=new MutationObserver(()=>{if(!loading)paint()});
observer.observe(document.documentElement,{childList:true,subtree:true});
fetch('/data/mlb/historical-players/'+encodeURIComponent(slug)+'.json').then(r=>{if(!r.ok)throw Error('Player data missing');return r.json()}).then(d=>{if(d.status!=='MLB_HISTORICAL_PLAYER_LEADERS'||d.slug!==slug)throw Error('Unexpected team data');dataset=d;paint()}).catch(e=>console.warn('MLB historical player data unavailable:',e.message));
document.addEventListener('change',e=>{if(e.target?.id==='wiseSeasonSelect')requestAnimationFrame(paint)});
})();
