/* Keep ranking column labels visible through page and horizontal scrolling. */
(() => {
 'use strict';
 if (!/(?:^|[/-])rankings(?:\/|$)/.test(location.pathname) || window.betwiseRankingHeaders) return;
 window.betwiseRankingHeaders = true;
 const states = new Map();
 const scrollSources = new WeakMap();
 function syncHorizontal(state, source) {
  const left=source.scrollLeft;
  if (state.expected.has(source) && Math.abs(state.expected.get(source)-left)<1) {
   state.expected.delete(source); return;
  }
  state.expected.delete(source);
  for (const target of [state.scroller,state.clip,state.track]) {
   if (target===source || Math.abs(target.scrollLeft-left)<1) continue;
   state.expected.set(target,left); target.scrollLeft=left;
  }
 }
 const scrollbarStyle=document.createElement('style');
 scrollbarStyle.textContent='[data-ranking-header-clip]{scrollbar-width:none!important}[data-ranking-header-clip]::-webkit-scrollbar{display:none}';
 document.head.appendChild(scrollbarStyle);
 let frame = 0;
 const visual = ['font','color','backgroundColor','borderTop','borderRight','borderBottom','borderLeft','padding','textAlign','verticalAlign','letterSpacing','textTransform','whiteSpace','lineHeight','boxSizing','borderCollapse','borderSpacing','borderRadius','display','alignItems','justifyContent','gap'];
 const schedule = () => { if (!frame) frame = requestAnimationFrame(update); };
 function offset() {
  let top = 0;
  document.querySelectorAll('.site-header').forEach(header => {
   const css = getComputedStyle(header), rect = header.getBoundingClientRect();
   if (['fixed','sticky'].includes(css.position) && rect.top <= 0 && rect.bottom > 0) top = Math.max(top, rect.bottom);
  });
  return top;
 }
 function refresh(state) {
  const {table, overlay} = state;
  const head = table.tHead;
  const copy = table.cloneNode(false);
  copy.removeAttribute('id');
  copy.append(head.cloneNode(true));
  const originals = [table, head, ...head.querySelectorAll('*')];
  const clones = [copy, copy.tHead, ...copy.tHead.querySelectorAll('*')];
  originals.forEach((node, i) => {
   const clone = clones[i], css = getComputedStyle(node);
   visual.forEach(prop => { clone.style[prop] = css[prop]; });
   clone.removeAttribute('id');
   if (clone.matches('a,button,input,select,[tabindex]')) clone.tabIndex = -1;
   if (node.tagName === 'TH' || node.tagName === 'TD') {
    const width = node.getBoundingClientRect().width + 'px';
    clone.style.width = clone.style.minWidth = clone.style.maxWidth = width;
    clone.style.boxSizing = 'border-box';
    if (css.position === 'sticky' && css.left !== 'auto') {
     clone.style.position = 'sticky'; clone.style.left = css.left; clone.style.zIndex = css.zIndex;
    }
   }
  });
  copy.style.width = copy.style.minWidth = copy.style.maxWidth = table.getBoundingClientRect().width + 'px';
  copy.style.tableLayout = 'fixed'; copy.style.margin = '0';
  // Forward controls to the real header, retaining each sport's sort/help handlers.
  copy.addEventListener('click', event => {
   if (event.target.closest('[role="scrollbar"]')) return;
   const cell = event.target.closest('th,td'); if (!cell) return;
   const row = cell.parentElement.rowIndex, column = cell.cellIndex;
   const real = head.rows[row]?.cells[column]; if (!real) return;
   const control = event.target.closest('button,a');
   if (control) {
    const controls = [...cell.querySelectorAll('button,a')];
    real.querySelectorAll('button,a')[controls.indexOf(control)]?.click();
   } else real.click();
   event.preventDefault(); event.stopPropagation();
   state.dirty = true; schedule();
  });
  // A persistent native scrollbar lives outside the replaceable header copy.
  // Repainting sort arrows or the original scrubber cannot interrupt its drag.
  copy.querySelectorAll('[role="scrollbar"]').forEach(bar => bar.closest('tr')?.remove());
  state.clip.replaceChildren(copy);
  state.headerHeight = copy.tHead.getBoundingClientRect().height;
  state.dirty = false;
 }
 function update() {
  frame = 0;
  document.querySelectorAll('table').forEach(table => {
   if (!table.tHead || table.closest('[data-ranking-header-overlay]') || states.has(table)) return;
   let scroller = table.parentElement;
   while (scroller !== document.body && !/auto|scroll|hidden/.test(getComputedStyle(scroller).overflowX)) scroller = scroller.parentElement;
   const overlay = document.createElement('div');
   overlay.dataset.rankingHeaderOverlay = ''; overlay.setAttribute('aria-hidden','true');
   Object.assign(overlay.style, {position:'fixed',zIndex:'90',overflow:'hidden',background:'#0d0d0d',boxShadow:'0 2px 0 #333',display:'none',overscrollBehavior:'contain'});
   const clip = document.createElement('div'); clip.dataset.rankingHeaderClip='';
   Object.assign(clip.style,{overflowX:'auto',overflowY:'hidden',overscrollBehaviorX:'contain',touchAction:'auto',webkitOverflowScrolling:'touch'});
   const track = document.createElement('div'); track.dataset.rankingHeaderScrollbar = '';
   Object.assign(track.style,{overflowX:'scroll',overflowY:'hidden',height:'18px',width:'100%',scrollbarWidth:'auto',background:'#222a25'});
   const size = document.createElement('div'); size.style.height = '1px'; track.append(size);
   overlay.append(clip,track); document.body.append(overlay);
   const state = {table,scroller,overlay,clip,track,size,expected:new WeakMap(),dirty:true}; states.set(table,state);
   for (const source of [scroller,clip,track]) {
    scrollSources.set(source,state);
    source.addEventListener('scroll',()=>syncHorizontal(state,source),{passive:true});
   }
   const resize = new ResizeObserver(() => { state.dirty = true; schedule(); });
   resize.observe(table); resize.observe(table.tHead); state.resize = resize;

  });
  const top = offset();
  states.forEach((state, table) => {
   if (!table.isConnected || !table.tHead) {state.overlay.remove(); state.resize.disconnect(); states.delete(table); return;}
   const rect = table.getBoundingClientRect(), head = table.tHead.getBoundingClientRect();
   const bounds = state.scroller === document.body ? rect : state.scroller.getBoundingClientRect();
   const left = Math.max(0,bounds.left), right = Math.min(document.documentElement.clientWidth,bounds.right);
   const active = rect.width > 0 && head.top < top && rect.bottom > top + head.height && right > left;
   const wasActive=state.overlay.style.display==='block';
   state.overlay.style.display = active ? 'block' : 'none';
   if (!active) return;
   const refreshed=state.dirty;
   if (refreshed) refresh(state);
   const hasScroll = state.scroller.scrollWidth > state.scroller.clientWidth + 1;
   state.track.style.display=hasScroll?'block':'none';
   state.size.style.width=state.scroller.scrollWidth+'px';
   Object.assign(state.overlay.style, {left:left+'px',top:top+'px',width:(right-left)+'px',height:(state.headerHeight+(hasScroll?18:0))+'px'});
   state.clip.style.height=state.headerHeight+'px';
   const scrollLeft = state.scroller === document.body ? Math.max(0,-rect.left) : state.scroller.scrollLeft + Math.max(0,-bounds.left);
   if (!wasActive || refreshed) {
    for (const target of [state.clip,state.track]) {
     if (Math.abs(target.scrollLeft-scrollLeft)<1) continue;
     state.expected.set(target,scrollLeft); target.scrollLeft=scrollLeft;
    }
   }
  });
 }
 new MutationObserver(records => {
  const external = records.some(record => !record.target.closest?.('[data-ranking-header-overlay]') && !((record.addedNodes.length+record.removedNodes.length)>0 && [...record.addedNodes,...record.removedNodes].every(node => node.nodeType === 1 && node.hasAttribute('data-ranking-header-overlay'))));
  if (!external) return;
  states.forEach(state => { if(records.some(record=>state.table===record.target || state.table.tHead?.contains(record.target))) state.dirty=true; }); schedule();
 }).observe(document.body,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['aria-sort','aria-expanded']});
 window.addEventListener('scroll',event=>{if(!scrollSources.has(event.target)) schedule();},{passive:true,capture:true});
 window.addEventListener('resize',() => {states.forEach(state => {state.dirty=true;}); schedule();},{passive:true});
 document.fonts?.ready.then(() => {states.forEach(state => {state.dirty=true;}); schedule();});
 schedule();
})();
