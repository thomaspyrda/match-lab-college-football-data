"""Recover blank player lists only, with exact team identity and scoring checks."""
import json
from collections import defaultdict, Counter
from datetime import datetime, timezone
from cbb_verified_source import ROOT, BASE, crosswalk, fetch, finite, save

def played(season):
    return {str(g['id']):g for ph in season.get('phases',{}).values() for g in ph.get('games',[])
            if g.get('status')=='final' and finite(g.get('points')) and finite(g.get('opponent_points'))
            and max(g['points'],g['opponent_points'])>2}

def convert(row):
    gp = row.get('games')
    if not finite(gp) or gp < 1 or not finite(row.get('points')): return None
    stats = {'gamesPlayed':gp, 'points':row['points']}
    for source,dest in [('minutes','avgMinutes'),('points','avgPoints'),('assists','avgAssists'),
                        ('steals','avgSteals'),('blocks','avgBlocks'),('turnovers','avgTurnovers')]:
        value=row.get(source)
        if finite(value): stats[dest]=value/gp
    reb=(row.get('rebounds') or {}).get('total')
    if finite(reb): stats.update(rebounds=reb,avgRebounds=reb/gp)
    for source,dest in [('fieldGoals','fieldGoalPct'),('threePointFieldGoals','threePointFieldGoalPct'),('freeThrows','freeThrowPct')]:
        shot=row.get(source) or {}; made,att=shot.get('made'),shot.get('attempted')
        if finite(made) and finite(att) and 0<=made<=att and att>0:stats[dest]=100*made/att
    return {'id':str(row.get('athleteSourceId') or 'cbbd:'+str(row['athleteId'])),
            'name':row['name'],'position':row.get('position'),'stats':stats}

def main():
    paths={p.stem:p for p in (ROOT/'data/cbb/teams').glob('*.json')}
    archives={s:json.loads(p.read_text()) for s,p in paths.items()}
    pending=defaultdict(list)
    for slug,a in archives.items():
        for year,s in a['seasons'].items():
            if 2016<=int(year)<=2026 and played(s) and not any((p.get('stats') or {}).get('gamesPlayed',0)>0 for p in s.get('players') or []):
                pending[int(year)].append(slug)
    identity=crosswalk();report={'before_missing':sum(map(len,pending.values())),'seasons':{},'remaining':[]}
    changed=set()
    for year,slugs in sorted(pending.items()):
        rows=fetch('/stats/player/season',season=year)
        if not isinstance(rows,list):raise ValueError('Unexpected player response')
        grouped=defaultdict(list)
        for row in rows:
            slug=identity.get(str(row.get('teamId')))
            if slug in slugs and row.get('season')==year:
                player=convert(row)
                if player:grouped[slug].append(player)
        counts=Counter(source_rows=len(rows),attempted=len(slugs))
        for slug in slugs:
            season=archives[slug]['seasons'][str(year)];games=played(season);players=grouped[slug]
            expected=sum(g['points'] for g in games.values());observed=sum(p['stats']['points'] for p in players)
            valid=players and abs(observed-expected)<.01 and len({p['id'] for p in players})==len(players)
            valid=valid and all(0<p['stats']['gamesPlayed']<=len(games) for p in players)
            if not valid:
                counts['unverified']+=1;report['remaining'].append({'team':slug,'season':year,'expected_points':expected,'source_points':observed,'source_players':len(players)})
                continue
            season['players']=sorted(players,key=lambda p:-(p['stats'].get('avgPoints') or 0))
            season['player_stats_source']={'url':BASE+'/stats/player/season?season='+str(year),
                'scope':'full season, regular season and postseason','validation':'Exact ESPN team crosswalk; player points equal all completed archived game scores',
                'games':len(games),'points':expected,'retrieved_at':datetime.now(timezone.utc).isoformat()}
            season.setdefault('sources',[]).append({'name':'CBBD verified full-season player statistics','url':season['player_stats_source']['url']})
            changed.add(slug);counts['recovered']+=1
        report['seasons'][str(year)]=dict(counts);print(year,dict(counts),flush=True)
        for slug in changed:save(paths[slug],archives[slug])
        save(ROOT/'data/cbb/player-gap-backfill-report.json',report)
    report['recovered_team_seasons']=sum(x.get('recovered',0) for x in report['seasons'].values())
    report['remaining_missing']=len(report['remaining']);save(ROOT/'data/cbb/player-gap-backfill-report.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='remaining'}),flush=True)
if __name__=='__main__':main()
