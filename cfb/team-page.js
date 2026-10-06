(() => {
 'use strict';
 const payload=JSON.parse(document.querySelector('#teamSeasonData').textContent);
 const select=document.querySelector('#seasonSelect');
 const escape=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const record=r=>`${r.wins}-${r.losses}${r.ties?'-'+r.ties:''}`;
 const card=(label,value)=>`<article class="snapshot-card"><b>${escape(value)}</b><span>${escape(label)}</span></article>`;
 function render(year) {
  const s=payload.seasons[year];
  document.querySelector('#snapshotTitle').textContent=`${year} regular season`;
  if(!s){
   document.querySelector('#snapshotGrid').innerHTML='<p class="archive-note">No FBS regular-season archive is loaded for this season. Earlier FCS seasons are outside this archive.</p>';
   document.querySelector('#seasonNote').textContent='Select another season to view available FBS results.';
   document.querySelector('#scheduleBody').innerHTML='<tr><td colspan="10">No verified regular-season results loaded.</td></tr>';return;
  }
  const values=[['Record',record(s.record)],['PPG',s.ppg.toFixed(1)],['PPG Allowed',s.ppg_allowed.toFixed(1)],['Home',record(s.home)],['Away',record(s.away)],['Neutral',record(s.neutral)],['Conference',record(s.conference_record)],['Games',s.games_played]];
  for(const [key,label] of [['ats','ATS · W-L-P'],['ou','O/U · O-U-P']]){const m=s[key];values.push([label,m.games?`${m.first}-${m.second}-${m.pushes}`:'—']);}
  document.querySelector('#snapshotGrid').innerHTML=values.map(([k,v])=>card(k,v)).join('');
  document.querySelector('#seasonNote').innerHTML=`${escape(year)} regular season · ${s.games_played} completed games · ${escape(s.conference||'Conference unavailable')}. Postseason and bowls are excluded. Scoring ranks compare ${s.rank_field_size} FBS teams with recorded results: PPG #${s.ppg_rank}; PPG allowed #${s.ppg_allowed_rank}. ATS coverage ${s.ats.games}/${s.games_played}; totals coverage ${s.ou.games}/${s.games_played}. Betting lines are source-reported; closing status and observation timestamps are not verified. Missing lines are excluded from market records. <a href="${escape(s.sources[0].url)}">View source data</a>.`;
  document.querySelector('#scheduleBody').innerHTML=s.games.map(g=>{
   const name=escape(g.opponent),opponent=g.opponent_url?`<a href="${escape(g.opponent_url)}">${name}</a>`:name;
   const vals=[g.week,g.date.slice(0,10),g.site,opponent,g.result,`${g.points}–${g.allowed}`,g.spread==null?'—':(g.spread>=0?'+':'')+g.spread,g.ats??'—',g.total??'—',g.ou??'—'];
   return '<tr>'+vals.map((v,i)=>`<td>${i===3?v:escape(v)}</td>`).join('')+'</tr>';
  }).join('');
 }
 function change(){render(select.value);const url=new URL(location.href);url.searchParams.set('season',select.value);history.replaceState(null,'',url);}
 select.addEventListener('change',change);
 const requested=new URL(location.href).searchParams.get('season');
 if(requested&&[...select.options].some(o=>o.value===requested)){select.value=requested;render(requested);}
 window.addEventListener('popstate',()=>{const year=new URL(location.href).searchParams.get('season');if(year&&[...select.options].some(o=>o.value===year)){select.value=year;render(year);}});
})();
