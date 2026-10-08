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
  let data = JSON.parse(seed.textContent);
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
  if (location.pathname.includes('/nba/teams/')) {
    const slug=location.pathname.split('/').filter(Boolean).at(-1);
    fetch('https://matchlab.parlaycalculator.bet/nba/teams/data/'+encodeURIComponent(slug)+'.json',{cache:'no-cache'})
      .then(res=>{if(!res.ok)throw new Error('No verified archive');return res.json()})
      .then(remote=>{
        if(!Array.isArray(remote.seasons))return;
        const byKey=new Map(remote.seasons.map(row=>[String(row.key),row]));
        data={...data,seasons:data.seasons.map(row=>byKey.get(String(row.key))||row)};
        document.dispatchEvent(new CustomEvent('betwise-nba-archive-loaded',{detail:data}));
        render();
      }).catch(()=>{});
  }
  select.addEventListener('change', () => {
    const url = new URL(location.href); url.searchParams.set('season', select.value);url.hash='history';history.replaceState(null,'',url);render();
  }); render();
})();


/* NBA team profile enhancement: shared across all 30 individual NBA pages.
   Only verified records are rendered; missing metrics remain explicitly unavailable. */
(() => {
  const seed = document.querySelector('#team-season-data');
  if (!seed || !location.pathname.includes('/nba/teams/') || location.pathname.replace(/\/+$/, '').endsWith('/nba/teams')) return;
  const select = document.querySelector('#season-select');
  const historyPanel = document.querySelector('#history');
  const tabs = document.querySelector('.research-tabs');
  if (!select || !historyPanel || !tabs || document.querySelector('#nba-team-overview')) return;
  let data;
  try { data = JSON.parse(seed.textContent); } catch { return; }
  let allSeasons = Array.isArray(data.seasons) ? data.seasons : [];
  const stylesheet = document.createElement('style');
  stylesheet.textContent = `
    .nba-team-section{margin:22px 0;padding:24px;background:#171b18;border:1px solid #353d35;border-radius:16px}
    .nba-team-section h2{font-size:23px;margin:0 0 8px;color:#fff}
    .nba-team-section .nba-muted{font-size:13px;color:#aab4aa;line-height:1.55;margin:0 0 16px}
    .nba-kpi-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
    .nba-kpi{background:#101510;border:1px solid #303830;border-radius:11px;padding:15px}
    .nba-kpi strong{display:block;color:#fff;font-size:24px;font-variant-numeric:tabular-nums}
    .nba-kpi small{display:block;color:#aab4aa;font-size:11px;letter-spacing:.04em;text-transform:uppercase;margin-top:7px}
    .nba-empty{background:#111611;color:#c6cec6;border:1px dashed #465146;padding:17px;border-radius:11px;font-size:14px;line-height:1.6}
    .nba-scroll{overflow-x:auto}
    .nba-data-table{border-collapse:collapse;min-width:660px;width:100%;font-size:13px}
    .nba-data-table th,.nba-data-table td{padding:12px;border-bottom:1px solid #343b34;text-align:left}
    .nba-data-table th{color:#b3beb3;font-size:11px;text-transform:uppercase}
    .nba-data-table td{color:#f2f4f2}
    .research-tabs a[href^="#nba-"]{white-space:nowrap}
    @media(max-width:680px){.nba-team-section{padding:16px}.nba-kpi-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.nba-kpi strong{font-size:21px}}
  `;
  document.head.append(stylesheet);
  const make = (tag, cls, value) => {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (value != null) el.textContent = String(value);
    return el;
  };
  const block = (id, title, description) => {
    const section = make('section', 'nba-team-section');
    section.id = id;
    section.append(make('h2', '', title), make('p', 'nba-muted', description));
    return section;
  };
  const overview = block('nba-team-overview', 'Season Snapshot', 'Verified team results and per-game production for the selected NBA season.');
  const schedule = block('nba-team-schedule', 'Schedule & Results', 'Completed games, opponent, venue and final score. Schedules are kept separate from advanced metrics.');
  const metrics = block('nba-team-metrics', 'Advanced Metrics', 'Possession-adjusted efficiency, shooting, rebounding and turnover metrics when supported by verified records.');
  const players = block('nba-team-players', 'Player Statistics', 'Season player averages and production when a verified team roster dataset is available.');
  const franchise = block('nba-team-franchise', 'Franchise History', 'Season achievements and awards require source-verified historical records.');
  historyPanel.before(overview);
  historyPanel.after(schedule, metrics, players, franchise);
  [
    ['#nba-team-overview','Overview'],
    ['#nba-team-schedule','Schedule'],
    ['#nba-team-metrics','Advanced Metrics'],
    ['#nba-team-players','Players'],
    ['#nba-team-franchise','Franchise History']
  ].forEach(([href,label]) => {
    const link = make('a','',label); link.href=href;
    tabs.insertBefore(link, tabs.querySelector('a[href$="/nba/teams/"]'));
  });
  const empty = (panel, msg) => panel.append(make('p','nba-empty',msg));
  const table = (panel, headers, rows) => {
    const scroll=make('div','nba-scroll'), t=make('table','nba-data-table'), thead=make('thead'), thr=make('tr'), tbody=make('tbody');
    headers.forEach(label=>thr.append(make('th','',label)));
    thead.append(thr);
    rows.forEach(values=>{const tr=make('tr');values.forEach(value=>tr.append(make('td','',value==null?'—':value)));tbody.append(tr)});
    t.append(thead,tbody);scroll.append(t);panel.append(scroll);
  };
  const first = (obj, keys) => keys.map(key=>obj?.[key]).find(value=>value!==undefined && value!==null);
  const value = v => v==null ? '—' : typeof v==='number' ? String(Math.round(v*10)/10) : String(v);
  const draw = () => {
    const season=allSeasons.find(row=>row.key===select.value);
    if (!season) return;
    [overview,schedule,metrics,players,franchise].forEach(section=>[...section.children].slice(2).forEach(child=>child.remove()));
    const record=season.record || {};
    const kpis=[
      ['Record',typeof record==='string'?record:first(record,['overall','display','record'])],
      ['Wins',first(record,['wins','w'])],
      ['Losses',first(record,['losses','l'])],
      ['Points / Game',first(season.metrics,['ppg','points_per_game','pointsPerGame'])]
    ];
    const grid=make('div','nba-kpi-grid');
    kpis.forEach(([label,v])=>{const card=make('div','nba-kpi');card.append(make('strong','',value(v)),make('small','',label));grid.append(card)});
    overview.append(grid);
    const games=Array.isArray(season.games)?season.games:[];
    if (games.length) table(schedule,['Date','Opponent','H/A','Result','Score'],games.map(g=>[g.date,g.opponent_name,g.location,g.result,g.score_for!=null&&g.score_against!=null?`${g.score_for}–${g.score_against}`:null]));
    else empty(schedule,'No verified game-by-game results are loaded for '+season.label+'. Games and upcoming schedules will appear once validated.');
    const metricNames={ortg:'Offensive Rating',drtg:'Defensive Rating',net_rating:'Net Rating',pace:'Pace',efg_pct:'Effective FG%',ts_pct:'True Shooting%',tov_pct:'Turnover Rate',orb_pct:'Offensive Rebound%',three_pct:'3-Point%',ft_rate:'Free Throw Rate',opp_efg_pct:'Opponent eFG%'};
    const entries=Object.entries(season.metrics||{}).filter(([key,v])=>Object.hasOwn(metricNames,key)&&typeof v==='number'&&Number.isFinite(v));
    if(entries.length) {
      const cells=make('div','nba-kpi-grid');
      entries.forEach(([key,v])=>{const card=make('div','nba-kpi');card.append(make('strong','',value(v)),make('small','',metricNames[key]));cells.append(card)});
      metrics.append(cells);
    } else empty(metrics,'Verified advanced statistics are not yet loaded for '+season.label+'. No placeholder rankings or estimated efficiency figures are shown.');
    const roster=season.players||season.roster||[];
    if(Array.isArray(roster)&&roster.length) table(players,['Player','GP','PPG','RPG','APG'],roster.map(p=>[p.name,p.games,value(first(p,['ppg','points_per_game'])??p.per_game?.points),value(first(p,['rpg','rebounds_per_game'])??p.per_game?.rebounds),value(first(p,['apg','assists_per_game'])??p.per_game?.assists)]));
    else empty(players,'No verified season player-statistics dataset is attached for '+season.label+'.');
    const honors=season.honors||season.awards||[];
    if(Array.isArray(honors)&&honors.length) table(franchise,['Achievement','Details'],honors.map(x=>[x.title||x.name,x.detail||x.year||season.label]));
    else empty(franchise,'Franchise titles, playoff achievements, and player awards will be shown after their source records are verified.');
  };
  select.addEventListener('change', draw);
  document.addEventListener('betwise-nba-archive-loaded', event => {
    allSeasons=event.detail.seasons||[];
    draw();
  });
  draw();
})();
