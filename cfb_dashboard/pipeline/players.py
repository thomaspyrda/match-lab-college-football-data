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
