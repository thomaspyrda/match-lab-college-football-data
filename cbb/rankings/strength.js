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
   for(const btn of table.querySelectorAll('[data-sort]')){const active=btn.dataset.sort===key;btn.parentElement.setAttribute('aria-sort',active?(direction===1?'ascending':'descending'):'none');btn.querySelector('.sort-arrow').textContent=active?(direction===1?' ↑':' ↓'):' ↕'}
  };
  for(const button of table.querySelectorAll('[data-sort]'))button.addEventListener('click',()=>{if(key===button.dataset.sort)direction*=-1;else{key=button.dataset.sort;direction=['rating','sd','offense','form','change'].includes(key)?-1:1}apply()});
  search.addEventListener('input',apply);conference.addEventListener('change',apply);apply();
 }
 function pinTableHeader(table){
  const viewport=table.closest('.strength-table-scroll'),frame=viewport.parentElement;
  const board=document.createElement('div');board.className='strength-board';frame.before(board);board.append(frame);
  const pinned=document.createElement('div');pinned.className='strength-sticky-head';
  const headerViewport=document.createElement('div');headerViewport.className='strength-table-scroll strength-header-scroll';
  const headerTable=document.createElement('table');headerTable.className=table.className;headerTable.setAttribute('aria-label','CBB ranking column controls');
  headerTable.append(table.tHead.cloneNode(true));headerViewport.append(headerTable);
  const bar=document.createElement('div');bar.className='strength-top-scrollbar';bar.tabIndex=0;
  bar.setAttribute('role','scrollbar');bar.setAttribute('aria-label','Scroll CBB ranking columns horizontally');bar.setAttribute('aria-controls',viewport.id='strength-table-viewport');bar.setAttribute('aria-orientation','horizontal');bar.setAttribute('aria-valuemin','0');
  const thumb=document.createElement('span');thumb.className='strength-scroll-thumb';thumb.setAttribute('aria-hidden','true');bar.append(thumb);
  pinned.append(headerViewport,bar);board.prepend(pinned);
  const originalCells=[...table.tHead.rows[0].cells],headerCells=[...headerTable.tHead.rows[0].cells];
  const sync=()=>{
   const max=Math.max(0,viewport.scrollWidth-viewport.clientWidth),track=bar.clientWidth;
   const width=max?Math.min(track,Math.max(44,track*viewport.clientWidth/viewport.scrollWidth)):track;
   thumb.style.width=width+'px';thumb.style.transform='translateX('+(max?viewport.scrollLeft/max*(track-width):0)+'px)';
   bar.setAttribute('aria-valuemax',String(Math.round(max)));bar.setAttribute('aria-valuenow',String(Math.round(viewport.scrollLeft)));bar.setAttribute('aria-disabled',max?'false':'true');
   if(Math.abs(headerViewport.scrollLeft-viewport.scrollLeft)>.5)headerViewport.scrollLeft=viewport.scrollLeft;
  };
  let pending=false;
  const update=()=>{
   if(pending)return;pending=true;
   requestAnimationFrame(()=>{
    pending=false;
    const row=[...table.tBodies[0].rows].find(r=>!r.hidden);
    if(row){
     headerTable.style.width=table.getBoundingClientRect().width+'px';
     [...row.cells].forEach((cell,i)=>{const width=cell.getBoundingClientRect().width;for(const property of ['width','minWidth','maxWidth'])headerCells[i].style[property]=width+'px'});
    }
    originalCells.forEach((cell,i)=>{
     headerCells[i].setAttribute('aria-sort',cell.getAttribute('aria-sort')||'none');
     const arrow=headerCells[i].querySelector('.sort-arrow');if(arrow)arrow.textContent=cell.querySelector('.sort-arrow').textContent;
    });
    sync();
   });
  };
  headerTable.addEventListener('click',event=>{const button=event.target.closest('button[data-sort]');if(button)table.querySelector('button[data-sort="'+button.dataset.sort+'"]').click()});
  viewport.addEventListener('scroll',sync,{passive:true});
  headerViewport.addEventListener('scroll',()=>{if(Math.abs(viewport.scrollLeft-headerViewport.scrollLeft)>.5)viewport.scrollLeft=headerViewport.scrollLeft},{passive:true});
  let dragging=false,offset=0;
  const move=clientX=>{const max=Math.max(0,viewport.scrollWidth-viewport.clientWidth),travel=bar.clientWidth-thumb.offsetWidth;if(max&&travel)viewport.scrollLeft=Math.min(travel,Math.max(0,clientX-bar.getBoundingClientRect().left-offset))/travel*max};
  bar.addEventListener('pointerdown',event=>{
   if(event.button!==0)return;
   const rect=thumb.getBoundingClientRect(),onThumb=event.clientX>=rect.left&&event.clientX<=rect.right;
   dragging=true;offset=onThumb?event.clientX-rect.left:thumb.offsetWidth/2;
   bar.setPointerCapture(event.pointerId);bar.classList.add('dragging');if(!onThumb)move(event.clientX);event.preventDefault();
  });
  bar.addEventListener('pointermove',event=>{if(dragging)move(event.clientX)});
  const stop=()=>{dragging=false;bar.classList.remove('dragging')};
  bar.addEventListener('pointerup',stop);bar.addEventListener('pointercancel',stop);bar.addEventListener('lostpointercapture',stop);
  bar.addEventListener('keydown',event=>{
   const max=viewport.scrollWidth-viewport.clientWidth;
   if(event.key==='ArrowLeft')viewport.scrollLeft-=100;
   else if(event.key==='ArrowRight')viewport.scrollLeft+=100;
   else if(event.key==='Home')viewport.scrollLeft=0;
   else if(event.key==='End')viewport.scrollLeft=max;
   else return;event.preventDefault();
  });
  if(window.ResizeObserver){const observer=new ResizeObserver(update);observer.observe(viewport);observer.observe(table)}
  window.addEventListener('resize',update);document.fonts?.ready.then(update);update();
  return {update};
 }
 const pop=document.createElement('div');pop.className='strength-help';pop.hidden=true;pop.id='strength-help';pop.setAttribute('role','tooltip');document.body.append(pop);let anchor=null;
 const close=()=>{if(anchor){anchor.setAttribute('aria-expanded','false');anchor.removeAttribute('aria-describedby')}anchor=null;pop.hidden=true};
 for(const button of document.querySelectorAll('[data-help]'))button.addEventListener('click',e=>{e.stopPropagation();if(anchor===button){close();return}close();anchor=button;pop.textContent=button.dataset.help;pop.hidden=false;button.setAttribute('aria-expanded','true');button.setAttribute('aria-describedby',pop.id);const r=button.getBoundingClientRect(),w=pop.getBoundingClientRect().width,h=pop.getBoundingClientRect().height;pop.style.left=Math.max(12,Math.min(innerWidth-w-12,r.left))+'px';pop.style.top=Math.max(12,Math.min(innerHeight-h-12,r.bottom+8))+'px'});
 document.addEventListener('click',close);document.addEventListener('keydown',e=>{if(e.key==='Escape')close()});window.addEventListener('resize',close);document.addEventListener('scroll',close,true);
})();
