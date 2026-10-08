(() => {
  // Use the NFL/CFB order as the other sports' archive sections are added.
  const orderTeamSections = () => {
    const schedule = document.querySelector('#schedule');
    const metrics = document.querySelector('#metrics');
    if (schedule && metrics && schedule.parentElement === metrics.parentElement && schedule.nextElementSibling !== metrics) metrics.before(schedule);
    const nav = document.querySelector('.team-subnav');
    const scheduleLink = nav?.querySelector('a[href="#schedule"]');
    const metricsLink = nav?.querySelector('a[href="#metrics"]');
    if (scheduleLink && metricsLink && scheduleLink.nextElementSibling !== metricsLink) metricsLink.before(scheduleLink);
  };
  orderTeamSections();
  const input = document.querySelector('#team-search');
  const group = document.querySelector('#group-filter');
  if (input && group) {
    const cards = [...document.querySelectorAll('[data-team-name]')];
    const filter = () => {
      const query = input.value.trim().toLocaleLowerCase();
      let count = 0;
      cards.forEach(card => {
        card.hidden = !card.dataset.teamName.includes(query) || (group.value && card.dataset.group !== group.value);
        if (!card.hidden) count++;
      });
      document.querySelectorAll('.conference-group').forEach(section => section.hidden = !section.querySelector('[data-team-name]:not([hidden])'));
      document.querySelectorAll('.league-section').forEach(section => section.hidden = !section.querySelector('.conference-group:not([hidden])'));
      document.querySelector('#search-status').textContent = `${count} ${count === 1 ? 'team' : 'teams'} shown`;
      document.querySelector('#empty-search').hidden = count !== 0;
    };
    input.addEventListener('input', filter); group.addEventListener('change', filter);
  }
  const select = document.querySelector('#season-select');
  const seed = document.querySelector('#team-season-data');
  if (!select || !seed) return;
  const data = JSON.parse(seed.textContent);
  const container = document.querySelector('#season-content');
  const requested = new URL(location.href).searchParams.get('season');
  if (requested && data.seasons.some(s => s.key === requested)) select.value = requested;
  const node = (tag, text) => {const el = document.createElement(tag); el.textContent = text; return el;};
  const render = () => {
    const season = data.seasons.find(s => s.key === select.value);
    container.replaceChildren();
    document.querySelector('#selected-season-label').textContent = `${season.label} season`;
    const games = season.games || [];
    if (!games.length) {
      const box = node('div', ''); box.className = 'coverage-message';
      const icon = node('span', '◷'); icon.setAttribute('aria-hidden', 'true'); box.append(icon);
      const copy = node('div', ''); copy.append(node('h3', 'Season data not added yet'));
      copy.append(node('p', `${season.label} results and statistics will appear here after they have been collected and checked. Missing data does not mean this team did not compete that season.`)); box.append(copy); container.append(box);
    } else {
      const wrap = node('div', ''); wrap.className = 'research-table-wrap';
      const table = node('table', ''); table.className = 'research-table';
      table.append(node('caption', `${season.label} game results`));
      const head = node('thead', ''); const row = node('tr', '');
      ['Date','Opponent','Location','Result','Score'].forEach(label => {const th=node('th',label);th.scope='col';row.append(th);}); head.append(row); table.append(head);
      const body = node('tbody', ''); games.forEach(game => {
        const tr = node('tr', ''); [game.date, game.opponent_name, game.location, game.result, game.score_for != null && game.score_against != null ? `${game.score_for}–${game.score_against}` : null].forEach(value => tr.append(node('td', value ?? 'Unavailable'))); body.append(tr);
      }); table.append(body); wrap.append(table);container.append(wrap);
    }
    const summary = node('div', ''); summary.className = 'coverage-summary';
    summary.append(node('span', `${games.length} verified games loaded`));
    summary.append(node('span', season.updated_at ? `Updated ${season.updated_at}` : 'Historical collection pending'));
    container.append(summary);
    if (season.sources?.length) {
      const sources=node('p','Sources: ');sources.className='research-source';
      season.sources.forEach(source=>{try{const url=new URL(source.url);if(url.protocol!=='https:')return;const a=node('a',source.name);a.href=url.href;sources.append(a,document.createTextNode(' '));}catch{}});container.append(sources);
    }
    orderTeamSections();
  };
  select.addEventListener('change', () => {
    const url = new URL(location.href); url.searchParams.set('season', select.value);url.hash='history';history.replaceState(null,'',url);render();
  }); render();
})();
