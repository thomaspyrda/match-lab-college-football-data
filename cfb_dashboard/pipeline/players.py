"""Five role-specific cards and qualified FBS passing PPA ranks."""
from cfb_dashboard.pipeline.availability import lookup


def enrich_players(teams, ppa_rows, passing, team_games, recent, metadata, reports, fbs_teams):
    ppa = {(str(row.get('team')), str(row.get('id'))): (row.get('averagePPA') or {}).get('pass') for row in ppa_rows}
    qualified = []
    for team, rows in teams.items():
        for row in rows:
            row.update(lookup(reports, (metadata.get(team) or {}).get('espn_id'), row.get('id'), row.get('name')))
            if row.get('position') != 'QB': continue
            attempts = passing.get((team, str(row.get('id'))), 0)
            value = ppa.get((team, str(row.get('id'))))
            minimum = 10
            row['recent_passing_role'] = recent.get((team, str(row.get('id'))), (0, 0))
            row['efficiency'] = {'label':'Passing PPA', 'value':value, 'rank':None, 'sample_size':attempts,
                'minimum':minimum, 'qualified':value is not None and attempts >= minimum and team in fbs_teams,
                'help':'CFBD average passing Predicted Points Added, excluding garbage time. FBS QB rank requires at least 10 pass attempts this season. Passing PPA differs from NFL EPA per Dropback.'}
            if row['efficiency']['qualified']: qualified.append(row)
    for rows in teams.values():
        for row in rows:
            if row.get('position') != 'QB': continue
            metric = row['efficiency']
            metric['qualifying_count'] = len(qualified)
            if metric['qualified']: metric['rank'] = 1 + sum(other['efficiency']['value'] > metric['value'] for other in qualified)


def select_players(rows):
    available = [row for row in rows if not row.get('unavailable')]
    quarterbacks = [row for row in available if row.get('position') == 'QB']
    qb = max(quarterbacks, key=lambda row:(row.get('recent_passing_role') or (0,0), row.get('pass') or 0), default=None)
    skills = sorted([row for row in available if row.get('position') in {'RB','WR','TE'}], key=lambda row:float(row.get('overall') or 0), reverse=True)
    chosen = [next((row for row in skills if row.get('position') == pos), None) for pos in ('RB','WR','TE')]
    # ID is authoritative; name is the fallback for incomplete provider rows.
    def identity(row): return str(row.get('id') or row.get('name'))
    seen = {identity(row) for row in chosen if row}
    extra = next((row for row in skills if identity(row) not in seen), None)
    return [qb, *chosen, extra]

PRODUCTION_FIELDS = {
    'completions': ('passing:COMPLETIONS', 'passing:CMP', 'passing:COMP'),
    'attempts': ('passing:ATT', 'passing:ATTEMPTS'),
    'passing_yards': ('passing:YDS',), 'passing_tds': ('passing:TD',),
    'interceptions': ('passing:INT',), 'carries': ('rushing:CAR', 'rushing:ATT'),
    'rushing_yards': ('rushing:YDS',), 'rushing_tds': ('rushing:TD',),
    'receptions': ('receiving:REC',), 'receiving_yards': ('receiving:YDS',),
    'receiving_tds': ('receiving:TD',),
}


def enrich_production(teams, season_rows, completed_games, canonicalize=lambda value: value):
    """Join reported season totals by team/player ID; averages use team games."""
    raw = {}
    names = {}
    for stat in season_rows:
        team = canonicalize(stat.get('team'))
        pid = str(stat.get('playerId') or '')
        if not team or not pid:
            continue
        key = (team, pid)
        field = str(stat.get('category') or '').lower() + ':' + str(stat.get('statType') or '').upper()
        value = stat.get('stat')
        bucket = raw.setdefault(key, {})
        if field in bucket and bucket[field] != value:
            raise ValueError(f'Conflicting season player stat: {team} {pid} {field}')
        bucket[field] = value
        name = str(stat.get('player') or '').strip().casefold()
        if name:
            names.setdefault((team, name), set()).add(key)
    games = {}
    seen = set()
    for game in completed_games:
        if not game.get('result'):
            continue
        gid = str(game.get('game_id'))
        if gid in seen:
            continue
        seen.add(gid)
        for side in ('home', 'away'):
            team = canonicalize(game.get(side))
            games[team] = games.get(team, 0) + 1
    for team, players in teams.items():
        for player in players:
            key = (team, str(player.get('id') or ''))
            values = raw.get(key)
            if values is None and not player.get('id'):
                matches = names.get((team, str(player.get('name') or '').strip().casefold()), set())
                if len(matches) == 1:
                    values = raw[next(iter(matches))]
            totals = {}
            for field, aliases in PRODUCTION_FIELDS.items():
                value = next((values[a] for a in aliases if a in values), None) if values else None
                try:
                    totals[field] = float(str(value).replace(',', '')) if value is not None else None
                except (TypeError, ValueError):
                    totals[field] = None
            combined = values.get('passing:C/ATT') if values else None
            if combined and '/' in str(combined):
                try:
                    cmp, att = (float(v) for v in str(combined).split('/', 1))
                    if totals['completions'] is None: totals['completions'] = cmp
                    if totals['attempts'] is None: totals['attempts'] = att
                except ValueError:
                    pass
            n = games.get(team, 0)
            player['production'] = {
                'totals': totals, 'team_games': n,
                'per_game': {field: value / n if value is not None and n else None for field, value in totals.items()},
                'average_basis': 'per completed team game',
                'source': 'CollegeFootballData /stats/player/season',
            }
