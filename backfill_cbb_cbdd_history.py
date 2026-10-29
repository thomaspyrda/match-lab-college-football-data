"""Authenticated CBBD historical lines and specialty stats; exact ESPN IDs and scores.
Never expose credentials. Missing paint values/default zeros are not observations.
"""
import os,json,math,time,calendar,urllib.request,urllib.parse,urllib.error
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime,timedelta,timezone
R=Path(__file__).resolve().parent;BASE='https://api.collegebasketballdata.com';KEY=os.getenv('CBBD_API_KEY','').strip()
def read(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n')
def fetch(path,params):
 url=BASE+path+'?'+urllib.parse.urlencode(params)
 for attempt in range(4):
  try:
   req=urllib.request.Request(url,headers={'Authorization':'Bearer '+KEY,'User-Agent':'BetWiseHistoricalImporter/1.0'})
   with urllib.request.urlopen(req,timeout=60) as r:d=json.load(r)
   if not isinstance(d,list):raise ValueError('Unexpected response type at '+path)
   return d
  except urllib.error.HTTPError as e:
   if e.code not in [429,500,502,503,504] or attempt==3:raise RuntimeError(f'CBBD {path} HTTP {e.code}') from None
   time.sleep(2**attempt)
  except (TimeoutError,OSError):
   if attempt==3:raise
   time.sleep(2**attempt)
def window(path,year,start,end):
 p={'season':year,'startDateRange':start.isoformat().replace('+00:00','Z'),'endDateRange':end.isoformat().replace('+00:00','Z')};rows=fetch(path,p)
 if len(rows)>=3000:
  if end-start<timedelta(days=1):raise RuntimeError('API truncation at daily slice')
  middle=start+(end-start)/2
  return window(path,year,start,middle)+window(path,year,middle+timedelta(microseconds=1),end)
 return rows
def valid(v,lo,hi):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and lo<=v<=hi

def main():
 if not KEY:raise RuntimeError('CBBD_API_KEY must be configured in repository Actions secrets')
 teams=[t['slug'] for t in read(R/'data/sports/team-registry.json')['teams'] if t['sport']=='cbb'];archives={s:read(R/f'data/cbb/teams/{s}.json') for s in teams};markets={s:read(R/f'data/cbb/markets/{s}.json') for s in teams};opponents=read(R/'data/cbb/opponent-metrics.json');audit=Counter();byyear={}
 for year in range(2016,2027):
  ys=str(year);lookup=defaultdict(dict);regular=defaultdict(set)
  for slug,a in archives.items():
   for phase,data in a['seasons'].get(ys,{}).get('phases',{}).items():
    for g in data.get('games',[]):
     if g.get('status')!='final':continue
     lookup[str(g['id'])][slug]=g
     if phase=='regular':regular[slug].add(str(g['id']))
  games={};lines={};boxes={}
  for cy,month in [(year-1,10),(year-1,11),(year-1,12),*[(year,m) for m in range(1,5)]]:
   start=datetime(cy,month,1,tzinfo=timezone.utc);end=start.replace(day=calendar.monthrange(cy,month)[1],hour=23,minute=59,second=59,microsecond=999999)
   for endpoint,dest in [('/games',games),('/lines',lines),('/games/teams',boxes)]:
    for row in window(endpoint,year,start,end):
     key=(str(row['gameId']),str(row['teamId'])) if endpoint=='/games/teams' else str(row.get('gameId',row.get('id')))
     dest[key]=row
  records=defaultdict(lambda:{'ats':[0,0,0],'ou':[0,0,0]});paint=defaultdict(dict);added=Counter()
  for cid,line in lines.items():
   game=games.get(cid)
   if not game or game.get('status')!='final':continue
   gid=str(game.get('sourceId',''));entries=lookup.get(gid,{})
   if not entries:audit['unmatched_source_game']+=1;continue
   ranked=sorted(line.get('lines',[]),key=lambda v:({'consensus':0,'teamrankings':1,'numberfire':2}.get(str(v.get('provider','')).lower(),3),str(v.get('provider',''))))
   spread=next((v for v in ranked if valid(v.get('spread'),-100,100)),None);total=next((v for v in ranked if valid(v.get('overUnder'),50,350)),None)
   for slug,g in entries.items():
    hp,ap=game.get('homePoints'),game.get('awayPoints')
    is_home=g['points']==hp and g['opponent_points']==ap
    is_away=g['points']==ap and g['opponent_points']==hp
    if is_home==is_away:audit['score_mismatch']+=1;continue
    out=markets[slug]['games'].setdefault(ys,{}).setdefault(gid,{})
    if spread:
     v=spread['spread']*(1 if is_home else -1);margin=g['points']-g['opponent_points']+v;result='W' if margin>0 else 'L' if margin<0 else 'P'
     if 'spread' not in out:added['new_spreads']+=1
     out.update(spread=v,ats=result,ats_provider=spread['provider'],ats_source=BASE+'/lines',line_type='provider historical line');records[slug]['ats'][['W','L','P'].index(result)]+=1
    if total:
     v=total['overUnder'];margin=g['points']+g['opponent_points']-v;result='O' if margin>0 else 'U' if margin<0 else 'P'
     if 'total' not in out:added['new_totals']+=1
     out.update(total=v,ou=result,ou_provider=total['provider'],ou_source=BASE+'/lines',line_type='provider historical line');records[slug]['ou'][['O','U','P'].index(result)]+=1
    out['source']=BASE+'/lines'
  for (cid,tid),box in boxes.items():
   game=games.get(cid)
   if not game:continue
   gid=str(game.get('sourceId',''))
   for slug,g in lookup.get(gid,{}).items():
    if gid not in regular[slug]:continue
    is_home=g['points']==game.get('homePoints') and g['opponent_points']==game.get('awayPoints')
    expected=str(game.get('homeTeamId' if is_home else 'awayTeamId'))
    if tid!=expected:continue
    own=box.get('teamStats',{}).get('points',{});opp=box.get('opponentStats',{}).get('points',{})
    if own.get('total')!=g['points'] or opp.get('total')!=g['opponent_points']:continue
    a,b=own.get('inPaint'),opp.get('inPaint')
    # Zero is commonly the source's missing-data default; do not count it as a real zero.
    if not valid(a,2,g['points']) or not valid(b,2,g['opponent_points']) or a%2 or b%2:continue
    paint[slug][gid]=(a,b)
  full=0;display_paint=0
  for slug,record in records.items():
   expected=len({gid for gid,entries in lookup.items() if slug in entries});record.update(source=BASE+'/lines',coverage='Matched final games; consensus, then teamrankings, then numberfire, then other providers per market',expected_games=expected)
   data=markets[slug];data.setdefault('cbbd_seasons',{})[ys]=record
   existing=data['seasons'].get(ys)
   if not existing or sum(record['ats'])>=sum(existing['ats']) and sum(record['ou'])>=sum(existing['ou']):data['seasons'][ys]=record
   if sum(record['ats'])==expected and sum(record['ou'])==expected:full+=1
  for slug,samples in paint.items():
   n=len(samples);expected=len(regular[slug]);coverage=n/expected if expected else 0
   if coverage<.95 or n<10:audit['paint_incomplete_team_seasons']+=1;continue
   values={'Points in the Paint':sum(x[0] for x in samples.values())/n,'Points in the Paint Allowed':sum(x[1] for x in samples.values())/n}
   entry=opponents['seasons'].setdefault(ys,{}).setdefault(slug,{'values':{},'ranks':{}});
   previous=entry.get('metric_samples',{}).get('Points in the Paint',{})
   if previous.get('method','').startswith('Official') and previous.get('games',0)>=n:continue
   entry['values'].update(values);entry.setdefault('metric_samples',{}).update({k:{'games':n,'expected_games':expected,'source':BASE+'/games/teams'} for k in values});display_paint+=1
  for key,descending in [('Points in the Paint',True),('Points in the Paint Allowed',False)]:
   items=sorted([(s,e['values'][key]) for s,e in opponents['seasons'].get(ys,{}).items() if e.get('metric_samples',{}).get(key) and key in e['values']],key=lambda x:x[1],reverse=descending);last=None;rank=0
   for i,(s,v) in enumerate(items):
    if v!=last:rank=i+1
    opponents['seasons'][ys][s]['ranks'][key]={'rank':rank,'size':len(items)};last=v
  byyear[ys]={'api_games':len(games),'api_line_games':len(lines),'team_season_records':len(records),'fully_lined_team_seasons':full,'paint_team_seasons':display_paint,**added};print(year,byyear[ys],flush=True)
  # Checkpoint validated season output so interrupted requests can be inspected as an artifact.
  for slug in teams:save(R/f'data/cbb/markets/{slug}.json',markets[slug])
  save(R/'data/cbb/opponent-metrics.json',opponents)
  save(R/'data/cbb/cbbd-backfill-report.json',{'source':BASE,'seasons':byyear,'audit':dict(audit),'paint_minimum_coverage':.95,'provider_order':['consensus','teamrankings','numberfire','other (alphabetical)']})
 assert len(byyear)==11
 print('Historical CBBD backfill completed',json.dumps(dict(audit)),flush=True)
if __name__=='__main__':main()
