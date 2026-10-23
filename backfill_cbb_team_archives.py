"""Collect provenance-backed CBB archives; never overwrite an existing season."""
import concurrent.futures as futures
import hashlib,json,math,time,urllib.request
from urllib.error import HTTPError
from uuid import uuid4
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SITE='https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/'
WEB='https://site.web.api.espn.com/apis/common/v3/sports/basketball/mens-college-basketball/statistics/'
CACHE=ROOT/'cbb-source-cache'
OUT=ROOT/'data/cbb/teams'

def get(url):
    path=CACHE/(hashlib.sha256(url.encode()).hexdigest()+'.json')
    if path.exists():return json.loads(path.read_text())
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url,timeout=35) as r:d=json.load(r)
            if d.get('error') or d.get('status')=='error':raise ValueError('Source API error response')
            path.parent.mkdir(parents=True,exist_ok=True)
            tmp=path.with_suffix('.'+uuid4().hex+'.tmp');tmp.write_text(json.dumps(d));tmp.replace(path)
            return d
        except HTTPError as e:
            if e.code==404:return {'unavailable':True}
            if attempt==2:raise
            time.sleep(attempt+1)
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)

def stats(row,categories):
    result={}
    names={c['name']:c['names'] for c in categories}
    for cat in row.get('categories',[]):
        for key,value in zip(names.get(cat['name'],[]),cat.get('values',[])):
            if isinstance(value,(int,float)) and math.isfinite(value):result[key]=value
    return result

def league(year,phase,kind):
    limit=300 if kind=='byteam' else 1000
    url=WEB+kind+f'?season={year}&seasontype={phase}&limit={limit}&isqualified=false'
    first=get(url)
    if first.get('requestedSeason',{}).get('year')!=year:
        if not first.get('athletes') and not first.get('teams'):
            print('Unavailable league player statistics',year,flush=True)
            return {}
        raise ValueError('Wrong source season '+str(year))
    key='teams' if kind=='byteam' else 'athletes'
    pages=[first]
    for page in range(2,first['pagination']['pages']+1):pages.append(get(url+f'&page={page}'))
    rows=[r for p in pages for r in p.get(key,[])]
    if len(rows)!=first['pagination']['count']:raise ValueError('Incomplete league pagination')
    result={}
    for p in pages:
        for row in p.get(key,[]):
            entity=row['team' if key=='teams' else 'athlete']
            if key=='teams': result[str(entity['id'])]=stats(row,p['categories'])
            else:
                tids=[str(t['id']) for t in entity.get('teams',[])]
                # Never assign a combined multi-team stat line to each team.
                if len(tids)!=1:continue
                values=stats(row,p['categories'])
                keep={'gamesPlayed','avgMinutes','avgPoints','avgRebounds','avgAssists','avgSteals','avgBlocks','fieldGoalPct','threePointFieldGoalPct','freeThrowPct','points','rebounds','assists','steals','blocks','turnovers'}
                result.setdefault(tids[0],[]).append(dict(id=str(entity['id']),name=entity['displayName'],position=entity.get('position',{}).get('abbreviation'),stats={k:v for k,v in values.items() if k in keep}))
    return result

def schedule(team,year,phase):
    url=SITE+f'teams/{team}/schedule?season={year}&seasontype={phase}'
    d=get(url)
    if d.get('requestedSeason',{}).get('year')!=year:
        if not d.get('events'):return []
        raise ValueError('Wrong schedule season')
    games=[]
    for e in d.get('events',[]):
        if e.get('season',{}).get('year')!=year:raise ValueError('Wrong event year')
        if int(e.get('seasonType',{}).get('type',phase))!=phase:continue
        c=e['competitions'][0]; own=next((t for t in c['competitors'] if str(t['id'])==team),None)
        if own is None:raise ValueError('Team mismatch')
        opp=next(t for t in c['competitors'] if t is not own)
        completed=c.get('status',e.get('status',{})).get('type',{}).get('completed',False)
        def score(row):
            s=row.get('score');s=s.get('value',s.get('displayValue')) if isinstance(s,dict) else s
            try:return int(float(s))
            except (TypeError,ValueError):return None
        a,b=score(own),score(opp)
        if completed and (a is None or b is None):raise ValueError('Final game without score')
        games.append(dict(id=e['id'],date=e['date'],opponent_id=str(opp['id']),opponent=opp['team']['displayName'],opponent_name=opp['team']['displayName'],location='Neutral' if c.get('neutralSite') else 'Home' if own['homeAway']=='home' else 'Away',points=a if completed else None,opponent_points=b if completed else None,result=('W' if a>b else 'L' if b>a else 'T') if completed else None,status='final' if completed else c.get('status',{}).get('type',{}).get('description','Scheduled'),source_url=url))
    if len(games)!=len({g['id'] for g in games}):raise ValueError('Duplicate games')
    return sorted(games,key=lambda g:(g['date'],g['id']))

def one(team,year,league_data):
    tid=str(team['espn_id']); phases={}
    for phase,label in [(2,'regular'),(3,'postseason')]:
        games=schedule(tid,year,phase)
        done=[g for g in games if g['status']=='final']
        metrics={}
        if done:
            core=f'https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/{year}/types/{phase}/teams/{tid}/statistics'
            raw=get(core)
            metrics={s['name']:s.get('value') for c in raw.get('splits',{}).get('categories',[]) for s in c.get('stats',[]) if isinstance(s.get('value'),(int,float)) and math.isfinite(s['value'])}
            # Never publish team statistics that disagree with the game archive.
            if metrics.get('gamesPlayed')!=len(done) or metrics.get('points')!=sum(g['points'] for g in done):
                metrics={}
        players=league_data[(year,2,'byathlete')].get(tid,[])
        players.sort(key=lambda p:-(p['stats'].get('avgPoints') or 0))
        phases[label]=dict(games=games,record=dict(wins=sum(g['result']=='W' for g in done),losses=sum(g['result']=='L' for g in done)),metrics=metrics,
            coverage='collected' if done or metrics or players else 'unavailable',completed_games=len(done))
    coach_url=SITE+f'teams/{tid}/roster?season={year}'
    roster=get(coach_url)
    coaches=[(' '.join(str(c.get(k,'')) for k in ('firstName','lastName'))).strip() for c in roster.get('coach',[])] if roster.get('season',{}).get('year')==year else []
    return dict(key=str(year),label=f'{year-1}–{str(year)[2:]}',team_id=tid,
        collected_at=datetime.now(timezone.utc).isoformat(),phases=phases,players=players,coaches=coaches,
        sources=[dict(name='ESPN team schedule',url=SITE+f'teams/{tid}/schedule?season={year}'),dict(name='ESPN team season statistics',url=f'https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/seasons/{year}/types/2/teams/{tid}/statistics'),dict(name='ESPN full-season player statistics',url=WEB+f'byathlete?season={year}&seasontype=2'),dict(name='ESPN coaching archive',url=coach_url)])

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--years',nargs='+',type=int,default=list(range(2016,2028)));p.add_argument('--workers',type=int,default=12);args=p.parse_args()
    teams=[t for t in json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'] if t['sport']=='cbb']
    OUT.mkdir(parents=True,exist_ok=True)
    league_data={};tasks=[(y,2,'byathlete') for y in args.years]
    with futures.ThreadPoolExecutor(max_workers=6) as pool:
        pending={pool.submit(league,*key):key for key in tasks}
        for f in futures.as_completed(pending):
            key=pending[f];league_data[key]=f.result();print('League',*key,len(league_data[key]),flush=True)
    completed=0;errors=[]
    def collect(team):
        path=OUT/(team['slug']+'.json');existing=json.loads(path.read_text()) if path.exists() else dict(team_id=str(team['espn_id']),slug=team['slug'],seasons={})
        assert existing['team_id']==str(team['espn_id'])
        for y in args.years:
            now=datetime.now(timezone.utc)
            active=now.year+(now.month>=7)
            if str(y) in existing['seasons'] and y<active:continue
            try:existing['seasons'][str(y)]=one(team,y,league_data)
            except Exception as e:
                errors.append(dict(team=team['slug'],year=y,error=str(e)))
                print('Failed',team['slug'],y,str(e),flush=True)
                continue
            temp=path.with_suffix('.'+uuid4().hex+'.tmp');temp.write_text(json.dumps(existing,ensure_ascii=False,separators=(',',':'))+'\n');temp.replace(path)
        return team['slug'],len(existing['seasons'])
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for slug,count in pool.map(collect,teams):
            completed+=1;print('Team',completed,len(teams),slug,count,flush=True)
    report=dict(team_count=len(teams),years=args.years,errors=errors)
    (ROOT/'data/cbb/backfill-report.json').write_text(json.dumps(report,indent=2)+'\n')
    if errors:raise SystemExit(f'{len(errors)} team-season collection errors; existing data preserved')
if __name__=='__main__':main()
