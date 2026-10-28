/* Small, non-modal definitions for dynamically rendered basketball statistics. */
(() => {
  let popup, owner;
  const nativePopover = 'showPopover' in HTMLElement.prototype;
  const isOpen = () => popup && (nativePopover ? popup.matches(':popover-open') : !popup.hidden);
  const close = (restoreFocus = false) => {
    if (!popup) return;
    if (nativePopover && popup.matches(':popover-open')) popup.hidePopover();
    if (!nativePopover) popup.hidden = true;
    const previous = owner;
    owner = null;
    previous?.setAttribute('aria-expanded', 'false');
    if (restoreFocus) previous?.focus({preventScroll: true});
  };
  const ensurePopup = () => {
    if (popup) return;
    popup = document.createElement('div');
    popup.id = 'stat-definition-popup';
    popup.className = 'stat-definition-popup';
    popup.setAttribute('role', 'dialog');
    popup.setAttribute('aria-modal', 'false');
    popup.setAttribute('aria-labelledby', 'stat-definition-title');
    popup.setAttribute('aria-describedby', 'stat-definition-copy');
    if (nativePopover) popup.setAttribute('popover', 'auto'); else popup.hidden = true;
    popup.innerHTML = '<div class="stat-definition-head"><strong id="stat-definition-title"></strong><button type="button" aria-label="Close definition">×</button></div><p id="stat-definition-copy"></p>';
    popup.querySelector('button').addEventListener('click', () => close(true));
    popup.addEventListener('toggle', () => {
      if (!isOpen() && owner) { owner.setAttribute('aria-expanded', 'false'); owner = null; }
    });
    document.body.append(popup);
  };
  document.addEventListener('click', event => {
    const button = event.target.closest?.('.info');
    if (!button?.dataset.tip) {
      if (isOpen() && !popup.contains(event.target)) close();
      return;
    }
    event.preventDefault();
    if (owner === button && isOpen()) { close(); return; }
    ensurePopup();
    close();
    owner = button;
    popup.querySelector('strong').textContent = (button.getAttribute('aria-label') || 'Definition').replace(/^About /, '');
    popup.querySelector('p').textContent = button.dataset.tip;
    button.setAttribute('aria-controls', popup.id);
    button.setAttribute('aria-expanded', 'true');
    if (nativePopover) popup.showPopover(); else popup.hidden = false;
    const anchor = button.getBoundingClientRect();
    const box = popup.getBoundingClientRect();
    const width = document.documentElement.clientWidth;
    const left = Math.max(12, Math.min(anchor.left + anchor.width / 2 - box.width / 2, width - box.width - 12));
    let top = anchor.bottom + 8;
    if (top + box.height > innerHeight - 12) top = anchor.top - box.height - 8;
    popup.style.left = left + 'px';
    popup.style.top = Math.max(12, Math.min(top, innerHeight - box.height - 12)) + 'px';
  });
  document.addEventListener('keydown', event => { if (event.key === 'Escape' && isOpen()) close(true); });
  document.addEventListener('scroll', event => { if (isOpen() && !popup.contains(event.target)) close(); }, {capture: true, passive: true});
  window.addEventListener('resize', () => close());
})();
