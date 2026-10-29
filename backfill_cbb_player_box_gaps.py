"""Reconstruct still-blank seasons from complete score-checked ESPN game boxes."""
import argparse, concurrent.futures, json, re, urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from backfill_cbb_player_gaps import played
from cbb_verified_source import ROOT, save

def targets():
    games={}
    for path in (ROOT/'data/cbb/teams').glob('*.json'):
        archive=json.loads(path.read_text())
        for year,season in archive['seasons'].items():
            if not 2016<=int(year)<=2026 or any((p.get('stats') or {}).get('gamesPlayed',0)>0 for p in season.get('players') or []):continue
            for gid,g in played(season).items():games.setdefault(gid,[]).append((path.stem,year,str(archive['team_id']),g))
    return games

def parse_players(group,expected):
    stat=group['statistics'][0];labels=stat['labels'];players=[]
    for row in stat['athletes']:
        if row.get('didNotPlay'):continue
        v=dict(zip(labels,row.get('stats',[])))
        if not all(re.fullmatch(r'\d+(?:\.\d+)?',str(v.get(k,''))) for k in ['MIN','PTS','REB','AST','TO','STL','BLK']):raise ValueError('Missing player stats')
        totals={k:float(v[k]) for k in ['MIN','PTS','REB','AST','TO','STL','BLK']}
        for label in ['FG','3PT','FT']:
            m=re.fullmatch(r'(\d+)-(\d+)',str(v.get(label,'')))
            if not m:raise ValueError('Missing player shooting')
            made,attempted=map(int,m.groups())
            if made>attempted:raise ValueError('Invalid shooting')
            totals[label+'M'],totals[label+'A']=made,attempted
        if 2*totals['FGM']+totals['3PTM']+totals['FTM']!=totals['PTS'] or totals['3PTM']>totals['FGM']:raise ValueError('Player scoring mismatch')
        a=row['athlete'];players.append({'id':str(a['id']),'name':a['displayName'],'position':a.get('position',{}).get('abbreviation'),'totals':totals})
    if not players or len({p['id'] for p in players})!=len(players) or sum(p['totals']['PTS'] for p in players)!=expected:raise ValueError('Incomplete team box')
    return players

def extract(item):
    gid,entries=item;url='https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event='+gid
    try:
        with urllib.request.urlopen(url,timeout=20) as response:d=json.load(response)
        header=d.get('header',{});comp=header.get('competitions',[{}])[0]
        if str(header.get('id'))!=gid or not comp.get('status',{}).get('type',{}).get('completed'):return [],'not_final'
        sides={str(c['id']):c for c in comp.get('competitors',[])}
        boxes={str(t['team']['id']):t for t in d.get('boxscore',{}).get('players',[])}
        output=[]
        day=datetime.fromisoformat(comp['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date()
        for slug,year,tid,g in entries:
            other=next(k for k in sides if k!=tid)
            expected=datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date()
            if day!=expected or int(sides[tid]['score'])!=g['points'] or int(sides[other]['score'])!=g['opponent_points']:continue
            try:players=parse_players(boxes[tid],g['points'])
            except (KeyError,ValueError,IndexError):continue
            output.append({'team':slug,'year':year,'game_id':gid,'source':url,'points':g['points'],'players':players})
        return output,'verified' if output else 'incomplete_box'
    except Exception as exc:return [],'request_or_parse_error:'+type(exc).__name__

def scan(args):
    selected=[v for i,v in enumerate(sorted(targets().items())) if i%args.shards==args.shard]
    output=[];audit=Counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,(rows,status) in enumerate(pool.map(extract,selected),1):
            output+=rows;audit[status]+=1
            if i%100==0:print(i,len(selected),dict(audit),flush=True)
    save(Path(args.output),{'games':output,'audit':dict(audit),'attempted_unique_games':len(selected)})
    print('Box scan finished',len(output),dict(audit),flush=True)

def merge(args):
    paths=sorted(Path(args.input_dir).rglob('player-box-shard-*.json'));assert len(paths)==args.shards
    groups=defaultdict(dict);audit=Counter();attempted=0
    for path in paths:
        d=json.loads(path.read_text());audit.update(d['audit']);attempted+=d['attempted_unique_games']
        for g in d['games']:groups[g['team'],g['year']][g['game_id']]=g
    report={'attempted_unique_games':attempted,'audit':dict(audit),'recovered':[],'remaining':[]}
    for path in (ROOT/'data/cbb/teams').glob('*.json'):
        a=json.loads(path.read_text());changed=False
        for year,season in a['seasons'].items():
            expected=played(season)
            if not 2016<=int(year)<=2026 or not expected or any((p.get('stats') or {}).get('gamesPlayed',0)>0 for p in season.get('players') or []):continue
            boxes=groups[path.stem,year]
            if set(boxes)!=set(expected):
                report['remaining'].append({'team':path.stem,'season':year,'verified_boxes':len(boxes),'expected_games':len(expected)});continue
            players={}
            for box in boxes.values():
                for row in box['players']:
                    p=players.setdefault(row['id'],{'id':row['id'],'name':row['name'],'position':row['position'],'games':0,'totals':Counter()})
                    p['games']+=1;p['totals'].update(row['totals'])
            rows=[]
            for p in players.values():
                t,gp=p['totals'],p['games'];stats={'gamesPlayed':gp,'points':t['PTS'],'rebounds':t['REB']}
                for key,label in [('MIN','avgMinutes'),('PTS','avgPoints'),('REB','avgRebounds'),('AST','avgAssists'),('TO','avgTurnovers'),('STL','avgSteals'),('BLK','avgBlocks')]:stats[label]=t[key]/gp
                for key,label in [('FG','fieldGoalPct'),('3PT','threePointFieldGoalPct'),('FT','freeThrowPct')]:
                    if t[key+'A']:stats[label]=100*t[key+'M']/t[key+'A']
                rows.append({'id':p['id'],'name':p['name'],'position':p['position'],'stats':stats})
            assert sum(p['stats']['points'] for p in rows)==sum(g['points'] for g in expected.values())
            season['players']=sorted(rows,key=lambda p:-(p['stats'].get('avgPoints') or 0))
            season['player_stats_source']={'scope':'full season, regular season and postseason','method':'Every archived completed game has a verified complete ESPN player box; all individual shooting arithmetic and team scoring totals agree','games':len(boxes),'game_sources':{gid:b['source'] for gid,b in boxes.items()},'retrieved_at':datetime.now(timezone.utc).isoformat()}
            season.setdefault('sources',[]).append({'name':'ESPN complete game-by-game player statistics','url':next(iter(boxes.values()))['source']})
            changed=True;report['recovered'].append({'team':path.stem,'season':year,'players':len(rows),'games':len(boxes)})
        if changed:save(path,a)
    report['recovered_team_seasons']=len(report['recovered']);report['remaining_missing']=len(report['remaining'])
    save(ROOT/'data/cbb/player-box-backfill-report.json',report)
    print('Recovered',len(report['recovered']),'remaining',len(report['remaining']),dict(audit),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--merge',action='store_true');p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=4);p.add_argument('--output',default='/tmp/player-box-shard-0.json');p.add_argument('--input-dir',default='/tmp/player-box-shards');args=p.parse_args()
    merge(args) if args.merge else scan(args)
