(()=>{
 'use strict';
 const table=document.querySelector('#strength-table');
 if(table){
  const body=table.tBodies[0],rows=[...body.rows],search=document.querySelector('#strength-search'),conference=document.querySelector('#strength-conference'),count=document.querySelector('#strength-count');
  let key=table.dataset.sort||'rank',direction=1;
  const apply=()=>{
   rows.sort((a,b)=>{let x=a.dataset[key],y=b.dataset[key];if(x===''&&y==='')return Number(a.dataset.rank)-Number(b.dataset.rank);if(x==='')return 1;if(y==='')return -1;let n=key==='name'||key==='conference'?x.localeCompare(y):Number(x)-Number(y);return direction*n||Number(a.dataset.rank)-Number(b.dataset.rank)});
   for(const row of rows){row.hidden=!(row.dataset.name.toLowerCase().includes(search.value.trim().toLowerCase())&&(!conference.value||row.dataset.conference===conference.value));body.append(row)}
   count.textContent=rows.filter(r=>!r.hidden).length+' teams';
   for(const btn of table.querySelectorAll('[data-sort]')){const active=btn.dataset.sort===key;btn.parentElement.setAttribute('aria-sort',active?(direction===1?'ascending':'descending'):'none');btn.querySelector('.sort-arrow').textContent=active?(direction===1?' ↑':' ↓'):' ↕'}
  };
  for(const button of table.querySelectorAll('[data-sort]'))button.addEventListener('click',()=>{if(key===button.dataset.sort)direction*=-1;else{key=button.dataset.sort;direction=['rating','offense','form','change'].includes(key)?-1:1}apply()});
  search.addEventListener('input',apply);conference.addEventListener('change',apply);apply();
 }
 const pop=document.createElement('div');pop.className='strength-help';pop.hidden=true;pop.id='strength-help';pop.setAttribute('role','tooltip');document.body.append(pop);let anchor=null;
 const close=()=>{if(anchor){anchor.setAttribute('aria-expanded','false');anchor.removeAttribute('aria-describedby')}anchor=null;pop.hidden=true};
 for(const button of document.querySelectorAll('[data-help]'))button.addEventListener('click',e=>{e.stopPropagation();if(anchor===button){close();return}close();anchor=button;pop.textContent=button.dataset.help;pop.hidden=false;button.setAttribute('aria-expanded','true');button.setAttribute('aria-describedby',pop.id);const r=button.getBoundingClientRect(),w=pop.getBoundingClientRect().width,h=pop.getBoundingClientRect().height;pop.style.left=Math.max(12,Math.min(innerWidth-w-12,r.left))+'px';pop.style.top=Math.max(12,Math.min(innerHeight-h-12,r.bottom+8))+'px'});
 document.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});window.addEventListener('resize',close);document.addEventListener('scroll',close,true);
})();
