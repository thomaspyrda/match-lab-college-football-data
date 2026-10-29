"""Verified full-game paint from the public service embedded by official schools.

Season IDs are discovered from official men's schedules, not guessed. NCAA school
IDs, date, opponent and both final scores must match our men's game archive.
"""
import argparse, gzip, hashlib, json, re, time, unicodedata, urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode, unquote
from zoneinfo import ZoneInfo
import backfill_cbb_official_paint as base

R=Path(__file__).resolve().parent

def extract(game, year, schools, archives, audit):
    if str(game.get('season_academic_year'))!=str(year):
        audit['wrong_season']+=1; return []
    if game.get('canceled') or game.get('is_exhibition') or game.get('stats_finalized') is not True:
        audit['unfinished_or_exhibition']+=1; return []
    competitors=game.get('competitors',[])
    if len(competitors)!=2:return []
    sides=[]
    for c in competitors:
        slug=schools.get(str(c.get('schoolId')))
        if not slug:audit['unknown_school']+=1
        totals=[x.get('statistic') or {} for x in (c.get('teamStats') or []) if x.get('period')==0]
        if len(totals)!=1:return []
        try:
            score=int(c['score']); paint=totals[0]['sPointsInThePaint']
            if isinstance(paint,bool) or not isinstance(paint,(int,float)) or int(paint)!=paint:return []
            paint=int(paint)
            if int(totals[0]['sPoints'])!=score or not 0<=paint<=score or paint%2:return []
        except (KeyError,TypeError,ValueError):return []
        sides.append((slug,score,paint))
    if sum(s[2] for s in sides)==0:audit['zero_defaults']+=1;return []
    # Historical WMT imports mix real UTC timestamps and calendar dates encoded
    # as midnight UTC. Resolve only against a unique exact matchup/final score.
    try:
        dt=datetime.fromisoformat(game['game_date'].replace('Z','+00:00'))
        days={dt.astimezone(ZoneInfo('America/New_York')).date().isoformat()}
        if dt.hour==0 and dt.minute==0:days.add(dt.date().isoformat())
    except (KeyError,TypeError,ValueError):return []
    out=[]
    for i,(slug,score,paint) in enumerate(sides):
        if not slug:continue
        opp,oppscore,opppaint=sides[1-i]
        season=archives.get(slug,{}).get('seasons',{}).get(str(year),{})
        matches={}
        for phase in season.get('phases',{}).values():
            for g in phase.get('games',[]):
                gd=datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
                if opp:
                    opponent_matches=str(g.get('opponent_id'))==str(archives[opp].get('team',{}).get('espn_id'))
                else:
                    def norm(s):return re.sub('[^a-z0-9]','',unicodedata.normalize('NFKD',s).encode('ascii','ignore').decode().lower())
                    name=norm(competitors[1-i].get('nameTabular',''))
                    opponent_matches=len(name)>=5 and norm(g.get('opponent','')).startswith(name)
                if g.get('status')=='final' and gd in days and g.get('points')==score and g.get('opponent_points')==oppscore and opponent_matches:
                    matches[g['id']]=g
        if len(matches)!=1:audit['archive_mismatch']+=1;continue
        matched=next(iter(matches.values()));day=datetime.fromisoformat(matched['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
        out.append({'date':day,'points':score,'opponent_points':oppscore,'paint_for':paint,'paint_against':opppaint,'format':'Official WMT full-game period 0 team totals','year':str(year),'game_id':next(iter(matches)),'team':slug,'opponent':opp,'source':f"https://api.wmt.games/api/statistics/games/{game['id']}"})
    audit['verified_observations']+=len(out)
    return out

def main(args):
    config=base.load(R/'data/cbb/wmt-paint-sources.json');schools=config['schools']
    archives={s:base.load(R/f'data/cbb/teams/{s}.json') for s in set(schools.values())}
    # Opponent IDs come from the registry, independent of archive metadata shape.
    registry={t['slug']:str(t['espn_id']) for t in base.load(R/'data/sports/team-registry.json')['teams'] if t['sport']=='cbb'}
    for slug,a in archives.items():a.setdefault('team',{})['espn_id']=registry[slug]
    cache=Path(args.cache_dir);cache.mkdir(parents=True,exist_ok=True)
    records=[];audit=Counter();seasons=[]
    for source in config['season_sources']:
        year=source['year'];cursor=None;seen=set();pages=0;start=len(records)
        if args.year and year!=args.year:continue
        while True:
            query={'season_id':source['season_id'],'per_page':100}
            if cursor:query['page']=unquote(cursor)
            url='https://api.wmt.games/api/statistics/games?'+urlencode(query)
            p=cache/(hashlib.sha256(url.encode()).hexdigest()+'.json')
            if p.exists():data=base.load(p)
            else:
                for attempt in range(3):
                    try:
                        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept-Encoding':'gzip','Accept':'application/json'})
                        with urllib.request.urlopen(req,timeout=45) as response:
                            raw=response.read();raw=gzip.decompress(raw) if response.headers.get('Content-Encoding')=='gzip' else raw
                        data=json.loads(raw);base.save(p,data);break
                    except Exception:
                        if attempt==2:raise
                        time.sleep(2)
            games=data['data'];pages+=1;audit['provider_games']+=len(games)
            for game in games:records+=extract(game,year,schools,archives,audit)
            print(year,'page',pages,'games',len(games),'observations',len(records)-start,flush=True)
            base.save(Path(args.output),{'records':records,'audit':dict(audit),'teams':[],'seasons':seasons})
            cursor=data.get('meta',{}).get('pagination',{}).get('next_page')
            if not cursor or not games:break
            assert cursor not in seen and pages<1000,'pagination loop'
            seen.add(cursor)
        seasons.append({**source,'pages':pages,'observations':len(records)-start})
        base.save(Path(args.output),{'records':records,'audit':dict(audit),'teams':[],'seasons':seasons})
    print(dict(audit),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--year',type=int);p.add_argument('--output',default='/tmp/wmt-paint/official-paint-shard-0.json');p.add_argument('--cache-dir',default='/tmp/cbb-wmt-paint-cache');main(p.parse_args())
