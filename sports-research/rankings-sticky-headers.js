/* Keep ranking column labels visible through page and horizontal scrolling. */
(() => {
 'use strict';
 if (!/(?:^|[/-])rankings(?:\/|$)/.test(location.pathname) || window.betwiseRankingHeaders) return;
 window.betwiseRankingHeaders = true;
 const states = new Map();
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
  copy.querySelectorAll('[role="scrollbar"]').forEach(bar => {
   const move = event => {
    const rect = bar.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    state.scroller.scrollLeft = ratio * (state.scroller.scrollWidth - state.scroller.clientWidth);
    schedule();
   };
   bar.addEventListener('pointerdown', event => { bar.setPointerCapture(event.pointerId); move(event); });
   bar.addEventListener('pointermove', event => { if (bar.hasPointerCapture(event.pointerId)) move(event); });
  });
  overlay.replaceChildren(copy);
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
   document.body.append(overlay);
   overlay.style.touchAction = 'pan-y';
   let touchStart;
   overlay.addEventListener('pointerdown', event => {
    if (event.pointerType === 'touch' && !event.target.closest('button,a,[role="scrollbar"]')) touchStart = {x:event.clientX,left:scroller.scrollLeft};
   });
   overlay.addEventListener('pointermove', event => {
    if (touchStart && event.pointerType === 'touch') {scroller.scrollLeft = touchStart.left + touchStart.x - event.clientX; schedule();}
   });
   ['pointerup','pointercancel','pointerleave'].forEach(type => overlay.addEventListener(type,() => {touchStart=null;}));
   const state = {table,scroller,overlay,dirty:true}; states.set(table,state);
   const resize = new ResizeObserver(() => { state.dirty = true; schedule(); });
   resize.observe(table); resize.observe(table.tHead); state.resize = resize;
   overlay.addEventListener('wheel', event => {
    if (event.deltaX || event.shiftKey) { scroller.scrollLeft += event.deltaX || event.deltaY; event.preventDefault(); schedule(); }
   }, {passive:false});
  });
  const top = offset();
  states.forEach((state, table) => {
   if (!table.isConnected || !table.tHead) {state.overlay.remove(); state.resize.disconnect(); states.delete(table); return;}
   const rect = table.getBoundingClientRect(), head = table.tHead.getBoundingClientRect();
   const bounds = state.scroller === document.body ? rect : state.scroller.getBoundingClientRect();
   const left = Math.max(0,bounds.left), right = Math.min(document.documentElement.clientWidth,bounds.right);
   const active = rect.width > 0 && head.top < top && rect.bottom > top + head.height && right > left;
   state.overlay.style.display = active ? 'block' : 'none';
   if (!active) return;
   if (state.dirty) refresh(state);
   Object.assign(state.overlay.style, {left:left+'px',top:top+'px',width:(right-left)+'px',height:head.height+'px'});
   state.overlay.scrollLeft = state.scroller === document.body ? Math.max(0,-rect.left) : state.scroller.scrollLeft + Math.max(0,-bounds.left);
  });
 }
 new MutationObserver(records => {
  const external = records.some(record => !record.target.closest?.('[data-ranking-header-overlay]') && ![...record.addedNodes,...record.removedNodes].every(node => node.nodeType === 1 && node.hasAttribute('data-ranking-header-overlay')));
  if (!external) return;
  states.forEach(state => { state.dirty = true; }); schedule();
 }).observe(document.body,{childList:true,subtree:true,characterData:true});
 window.addEventListener('scroll',schedule,{passive:true,capture:true});
 window.addEventListener('resize',() => {states.forEach(state => {state.dirty=true;}); schedule();},{passive:true});
 document.fonts?.ready.then(() => {states.forEach(state => {state.dirty=true;}); schedule();});
 schedule();
})();
