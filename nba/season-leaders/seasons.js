(() => {
  const select = document.querySelector('#nba-leaders-season');
  if (!select) return;
  select.addEventListener('change', () => {
    const path = select.value;
    if (/^\/nba\/season-leaders\/(?:\d{4}\/)?$/.test(path)) {
      window.location.assign(path);
    }
  });
})();
