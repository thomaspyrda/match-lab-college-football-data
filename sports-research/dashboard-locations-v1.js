(()=>{'use strict';
 const sport=document.currentScript.dataset.sport;
 const h=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const teamId=t=>String(t.espn_id||t.id||t.team_id||'').split(':').pop();
 let locationData=null;
 function byLocation(game,colors=[]){
  const neutral=!!(game.neutral||game.context?.neutral_site);
  const sides=[game.away,game.home];
  const roles=['Road','Home'],places=['Away','Home'];
  const trendRows=game.market_trends||game.trends||[];
  const split=(t,i)=>{
   if(neutral)return null;
   const own=t.location_splits?.[places[i]]||t.profile?.location_markets?.[places[i]];
   const fresh=locationData&&Date.now()-Date.parse(locationData.updated_at)<48*3600000;
   const fallback=fresh?(locationData.teams?.[teamId(t)]||locationData.teams?.[t.abbr])?.[places[i]]:null;
   return own?.ppg!=null?own:{...fallback,...own,...(own?.ppg==null&&fallback?{ppg:fallback.ppg,record:fallback.record,wins:fallback.wins,losses:fallback.losses,games:fallback.games}:{})};
  };
  const market=(t,i,type)=>{
   if(neutral)return '—';
   const r=split(t,i)?.[type];
   if(r)return r.lined_games?`${type==='ats'?r.wins:r.overs}–${type==='ats'?r.losses:r.unders}${r.pushes?'–'+r.pushes:''}`:'—';
   const labels=type==='ats'?['ATS by location','ATS in this venue role']:['O/U by location','O/U in this venue role'];
   const raw=trendRows.find(r=>labels.includes(r.label))?.[i?'home':'away'];
   if(!raw)return '—';
   const parts=String(raw).replace(/^(Road|Away|Home)\s*·\s*/i,'').replace(/\s+O\/U$/i,'').split(/[–-]/);
   if(parts.length===3&&Number(parts[2])===0)parts.pop();
   return parts.join('–');
  };
  const record=(t,i)=>{const r=split(t,i);if(!r?.games)return '—';return r.record||`${r.wins}–${r.losses}${r.ties?'–'+r.ties:''}`};
  const scoring=(t,i)=>{const r=split(t,i);return r?.games&&r.ppg!=null?Number(r.ppg).toFixed(1):'—'};
  const row=(label,fn)=>`<article class="context-card context-card--compact"><strong>${h(label)}</strong><div class="context-sides">${sides.map((t,i)=>`${i?'<i>VS</i>':''}<span style="--team-color:${h(colors[i]||t.color||'#fff')}"><small>${h(t.abbr||t.name)}</small><b>${neutral?'':roles[i]+' · '}${h(fn(t,i))}</b></span>`).join('')}</div></article>`;
  return `<section class="context-panel bw-by-location"><div class="context-title"><span>⌂</span><div><h4>By Location</h4><p>Season-to-date stats for each team’s role in this matchup.</p></div></div><div class="context-grid">${row(sport==='mlb'?'Run Line (ATS) by location':'ATS by location',(t,i)=>market(t,i,'ats'))}${row('O/U by location',(t,i)=>market(t,i,'ou'))}${row('Win-Loss by location',record)}${row(sport==='mlb'?'Runs per game by location':'PPG by location',scoring)}</div><p class="subtle bw-location-note">Visitor: road games. Host: home games. ATS: covers–noncovers. O/U: overs–unders. A third number appears only for pushes or ties. Missing lines are excluded. Home/road splits exclude neutral-site games.</p></section>`;
 }
 async function refreshLocations(){
  try{const r=await fetch('data/location-records.json',{cache:'no-store'});if(!r.ok)throw Error();locationData=await r.json();document.dispatchEvent(new CustomEvent('betwise-availability-updated'))}catch{}
 }

 window.BetWiseDashboardUX.byLocation=byLocation;refreshLocations();setInterval(refreshLocations,300000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refreshLocations()});
})();
