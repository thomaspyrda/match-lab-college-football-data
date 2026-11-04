(()=>{
 'use strict';
 const table=document.querySelector('#strength-table');
 if(table){
  const pinned=pinTableHeader(table);
  const body=table.tBodies[0],rows=[...body.rows],search=document.querySelector('#strength-search'),conference=document.querySelector('#strength-conference'),count=document.querySelector('#strength-count');
  let key=table.dataset.sort||'rank',direction=1;
  const apply=()=>{
   rows.sort((a,b)=>{let x=a.dataset[key],y=b.dataset[key];if(x===''&&y==='')return Number(a.dataset.rank)-Number(b.dataset.rank);if(x==='')return 1;if(y==='')return -1;let n=key==='name'||key==='conference'?x.localeCompare(y):Number(x)-Number(y);return direction*n||Number(a.dataset.rank)-Number(b.dataset.rank)});
   for(const row of rows){row.hidden=!(row.dataset.name.toLowerCase().includes(search.value.trim().toLowerCase())&&(!conference.value||row.dataset.conference===conference.value));body.append(row)}
   pinned.update();
   count.textContent=rows.filter(r=>!r.hidden).length+' teams';
   for(const btn of table.querySelectorAll('[data-sort]')){const active=btn.dataset.sort===key;btn.parentElement.setAttribute('aria-sort',active?(direction===1?'ascending':'descending'):'none');btn.querySelector('.sort-arrow').textContent=''}
  };
  for(const button of table.querySelectorAll('[data-sort]'))button.addEventListener('click',()=>{if(key===button.dataset.sort)direction*=-1;else{key=button.dataset.sort;direction=['rating','sd','offense','form','change'].includes(key)?-1:1}apply()});
  search.addEventListener('input',apply);conference.addEventListener('change',apply);apply();
 }
 function pinTableHeader(table){
  // One real table header: no cloned header, hidden overlay or duplicated columns.
  const viewport=table.closest('.strength-table-scroll');
  const frame=viewport.parentElement;
  const board=document.createElement('div');board.className='strength-board';
  frame.before(board);board.append(frame);
  const bar=document.createElement('div');bar.className='strength-top-scrollbar';
  bar.tabIndex=0;bar.setAttribute('role','scrollbar');
  bar.setAttribute('aria-label','Scroll CBB ranking columns horizontally');
  bar.setAttribute('aria-controls',viewport.id='strength-table-viewport');
  bar.setAttribute('aria-orientation','horizontal');bar.setAttribute('aria-valuemin','0');
  const thumb=document.createElement('span');thumb.className='strength-scroll-thumb';bar.append(thumb);
  const scrollRow=table.tHead.insertRow();scrollRow.className='strength-scrollbar-row';
  const scrollCell=document.createElement('th');scrollCell.colSpan=table.tHead.rows[0].cells.length;
  scrollCell.append(bar);scrollRow.append(scrollCell);
  const sync=()=>{
   bar.style.width=viewport.clientWidth+'px';
   const max=Math.max(0,viewport.scrollWidth-viewport.clientWidth),width=bar.clientWidth;
   const size=max?Math.min(width,Math.max(44,width*viewport.clientWidth/viewport.scrollWidth)):width;
   thumb.style.width=size+'px';
   thumb.style.transform='translateX('+(max?viewport.scrollLeft/max*(width-size):0)+'px)';
   bar.setAttribute('aria-valuemax',String(Math.round(max)));
   bar.setAttribute('aria-valuenow',String(Math.round(viewport.scrollLeft)));
   bar.setAttribute('aria-disabled',max?'false':'true');
  };
  let dragging=false,offset=0;
  const move=x=>{
   const max=viewport.scrollWidth-viewport.clientWidth,travel=bar.clientWidth-thumb.offsetWidth;
   if(max>0&&travel>0)viewport.scrollLeft=Math.max(0,Math.min(travel,x-bar.getBoundingClientRect().left-offset))/travel*max;
  };
  bar.addEventListener('pointerdown',e=>{
   if(e.button!==0)return;
   const rect=thumb.getBoundingClientRect();
   const hit=e.clientX>=rect.left&&e.clientX<=rect.right;
   dragging=true;offset=hit?e.clientX-rect.left:thumb.offsetWidth/2;
   bar.setPointerCapture(e.pointerId);bar.classList.add('dragging');if(!hit)move(e.clientX);e.preventDefault();
  });
  bar.addEventListener('pointermove',e=>{if(dragging)move(e.clientX)});
  const stop=()=>{dragging=false;bar.classList.remove('dragging')};
  for(const ev of ['pointerup','pointercancel','lostpointercapture'])bar.addEventListener(ev,stop);
  bar.addEventListener('keydown',e=>{
   if(e.key==='ArrowLeft')viewport.scrollLeft-=100;
   else if(e.key==='ArrowRight')viewport.scrollLeft+=100;
   else if(e.key==='Home')viewport.scrollLeft=0;
   else if(e.key==='End')viewport.scrollLeft=viewport.scrollWidth;
   else return;e.preventDefault();
  });
  viewport.addEventListener('scroll',sync,{passive:true});
  window.addEventListener('resize',sync);
  if(window.ResizeObserver){const observer=new ResizeObserver(sync);observer.observe(viewport);observer.observe(table)}
  requestAnimationFrame(sync);
  return {update:sync};
 }
 const pop=document.createElement('div');pop.className='strength-help';pop.hidden=true;pop.id='strength-help';pop.setAttribute('role','tooltip');document.body.append(pop);let anchor=null;
 const close=()=>{if(anchor){anchor.setAttribute('aria-expanded','false');anchor.removeAttribute('aria-describedby')}anchor=null;pop.hidden=true};
 for(const button of document.querySelectorAll('[data-help]'))button.addEventListener('click',e=>{e.stopPropagation();if(anchor===button){close();return}close();anchor=button;pop.textContent=button.dataset.help;pop.hidden=false;button.setAttribute('aria-expanded','true');button.setAttribute('aria-describedby',pop.id);const r=button.getBoundingClientRect(),w=pop.getBoundingClientRect().width,h=pop.getBoundingClientRect().height;pop.style.left=Math.max(12,Math.min(innerWidth-w-12,r.left))+'px';pop.style.top=Math.max(12,Math.min(innerHeight-h-12,r.bottom+8))+'px'});
 document.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});window.addEventListener('resize',close);document.addEventListener('scroll',close,true);
})();
