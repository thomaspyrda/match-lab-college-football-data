"""Target missing paint games; require explicit nonzero, score-checked box totals."""
import argparse, concurrent.futures, json, math, re, urllib.request
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from backfill_cbb_official_paint import R, load, save, completed_stat_game

def source_records():
    records=load(R/'data/cbb/official-paint-observations.json')['records']
    path=R/'data/cbb/espn-paint-observations.json'
    if path.exists():records+=load(path)['records']
    return {(r['team'],str(r['game_id'])):r for r in records if not r.get('conflict')}

def targets():
    existing=source_records();games={};identity={}
    for gap in load(R/'data/cbb/paint-coverage-report.json')['remaining_gaps']:
        slug,year=gap['team'],gap['season'];a=load(R/f'data/cbb/teams/{slug}.json');identity[str(a['team_id'])]=slug
        for g in a['seasons'][year]['phases']['regular']['games']:
            if completed_stat_game(g) and (slug,str(g['id'])) not in existing:
                games.setdefault(str(g['id']),[]).append((slug,year,str(a['team_id']),g))
    return games

def extract(gid,entries):
    url='https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event='+gid
    try:
        with urllib.request.urlopen(url,timeout=20) as response:d=json.load(response)
        event=d.get('header',{});competition=event.get('competitions',[{}])[0]
        if str(event.get('id'))!=gid or not competition.get('status',{}).get('type',{}).get('completed'):return [],'not_final'
        comp={str(t['id']):t for t in competition.get('competitors',[])}
        sides=d.get('boxscore',{}).get('teams',[])
        if len(sides)!=2 or len(comp)!=2:return [],'missing_box'
        values={}
        for side in sides:
            tid=str(side['team']['id']);stats={s['name']:s.get('displayValue') for s in side.get('statistics',[])}
            paint=stats.get('pointsInPaint')
            if not re.fullmatch(r'\d+',str(paint or '')):return [],'missing_paint'
            paint=int(paint)
            fg=[int(x) for x in str(stats.get('fieldGoalsMade-fieldGoalsAttempted','')).split('-')]
            threes=[int(x) for x in str(stats.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted','')).split('-')]
            ft=[int(x) for x in str(stats.get('freeThrowsMade-freeThrowsAttempted','')).split('-')]
            score=int(comp[tid]['score'])
            if not 0<paint<=2*(fg[0]-threes[0]) or paint%2 or 2*fg[0]+threes[0]+ft[0]!=score:return [],'zero_default_or_inconsistent_box'
            values[tid]=(paint,score)
        records=[]
        day=datetime.fromisoformat(event['competitions'][0]['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
        for slug,year,tid,g in entries:
            other=next(k for k in comp if k!=tid);own,opp=values[tid],values[other]
            expected_day=datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
            if own[1]!=g['points'] or opp[1]!=g['opponent_points'] or day!=expected_day:continue
            records.append({'team':slug,'year':year,'game_id':gid,'date':day,'points':own[1],
                'opponent_points':opp[1],'paint_for':own[0],'paint_against':opp[0],
                'source':url,'format':'ESPN whole-game team box; exact IDs, date, both final scores and shooting arithmetic verified'})
        return records,'verified' if records else 'identity_score_date_mismatch'
    except Exception as exc:return [],'request_or_parse_error:'+type(exc).__name__

def scan(args):
    selected=[x for i,x in enumerate(sorted(targets().items())) if i%args.shards==args.shard]
    records=[];audit=Counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for index,(rows,reason) in enumerate(pool.map(lambda x:extract(*x),selected),1):
            records+=rows;audit[reason]+=1
            if index%100==0:print('Scanned',index,len(selected),dict(audit),flush=True)
    save(Path(args.output),{'records':records,'audit':dict(audit),'attempted_games':len(selected)})
    print('Scan complete',len(records),dict(audit),flush=True)

def merge(args):
    paths=sorted(Path(args.input_dir).rglob('espn-paint-shard-*.json'))
    assert len(paths)==args.shards
    official=source_records();prior=R/'data/cbb/espn-paint-observations.json'
    records={(r['team'],str(r['game_id'])):r for r in load(prior)['records']} if prior.exists() else {}
    audit=Counter();attempted=0
    for path in paths:
        data=load(path);audit.update(data['audit']);attempted+=data['attempted_games']
        for r in data['records']:
            key=r['team'],str(r['game_id'])
            if key in official and (official[key]['paint_for'],official[key]['paint_against'])!=(r['paint_for'],r['paint_against']):raise ValueError('Paint source conflict')
            records[key]=r
    save(prior,{'records':list(records.values())});combined=source_records();groups=defaultdict(dict)
    for (slug,gid),r in combined.items():groups[r['year'],slug][gid]=r
    metrics=load(R/'data/cbb/opponent-metrics.json');added=[]
    for gap in load(R/'data/cbb/paint-coverage-report.json')['remaining_gaps']:
        slug,year=gap['team'],gap['season'];season=load(R/f'data/cbb/teams/{slug}.json')['seasons'][year]
        games={str(g['id']):g for g in season['phases']['regular']['games'] if completed_stat_game(g)}
        samples=[r for gid,r in groups[year,slug].items() if gid in games and r['points']==games[gid]['points'] and r['opponent_points']==games[gid]['opponent_points']]
        n=len(samples)
        if n<10 or n/len(games)<.95:continue
        entry=metrics['seasons'].setdefault(year,{}).setdefault(slug,{'values':{},'ranks':{}})
        for label,key in [('Points in the Paint','paint_for'),('Points in the Paint Allowed','paint_against')]:
            entry['values'][label]=sum(r[key] for r in samples)/n
            entry.setdefault('metric_samples',{})[label]={'games':n,'expected_games':len(games),
                'source':'ESPN whole-game boxes and verified official school archives',
                'observations_sources':['/data/cbb/espn-paint-observations.json','/data/cbb/official-paint-observations.json'],
                'method':'Verified combined whole-game paint; exact team identity, date and final scores'}
        added.append({'team':slug,'season':year,'games':n,'expected_games':len(games)})
    for year,teams in metrics['seasons'].items():
        for label,descending in [('Points in the Paint',True),('Points in the Paint Allowed',False)]:
            board=sorted([(s,t['values'][label]) for s,t in teams.items() if t.get('values',{}).get(label) is not None],key=lambda v:v[1],reverse=descending)
            last=None;rank=0
            for i,(slug,value) in enumerate(board,1):
                if value!=last:rank=i
                teams[slug].setdefault('ranks',{})[label]={'rank':rank,'size':len(board)};last=value
    save(R/'data/cbb/opponent-metrics.json',metrics)
    save(R/'data/cbb/espn-paint-gap-report.json',{'attempted_games':attempted,'audit':dict(audit),'verified_team_game_observations':len(records),'newly_filled_team_seasons':added})
    print('Newly filled paint seasons',len(added),'verified records',len(records),dict(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--merge',action='store_true');p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=3);p.add_argument('--output',default='/tmp/espn-paint-shard-0.json');p.add_argument('--input-dir',default='/tmp/espn-paint-shards');args=p.parse_args()
    merge(args) if args.merge else scan(args)
