"""Extract historical paint from public official men's box scores, never half totals.
Every observation must match an archived school, date and both final scores.
"""
import argparse,json,re,urllib.request,urllib.error,html,time,threading,hashlib
from pathlib import Path
from collections import defaultdict,Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor,as_completed
R=Path(__file__).resolve().parent

def load(p):return json.loads(p.read_text())
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n')
def ref(data,i):return data[i] if isinstance(i,int) and 0<=i<len(data) else None

def parse_nuxt(s):
 m=re.search(r'<script\b[^>]*\bid=["\']__NUXT_DATA__["\'][^>]*>(.*?)</script>',s,re.S)
 if not m:return None
 try:data=json.loads(m[1])
 except (ValueError,TypeError):return None
 if not isinstance(data,list):return None
 for b in data:
  if not isinstance(b,dict) or not all(k in b for k in ['homeTeam','visitingTeam','gameDate','homeTeamScore','visitingTeamScore']):continue
  if ref(data,b.get('itsWomens')) is not False:continue
  def side(key):
   t=ref(data,b[key]);tot=ref(data,t.get('totals')) if isinstance(t,dict) else None;sp=ref(data,tot.get('special')) if isinstance(tot,dict) else None
   if not isinstance(sp,dict) or 'pointsInThePaint' not in sp:return None
   try:return int(ref(data,sp['pointsInThePaint']))
   except (ValueError,TypeError):return None
  try:
   hs,vs=int(ref(data,b['homeTeamScore'])),int(ref(data,b['visitingTeamScore']));hp,vp=side('homeTeam'),side('visitingTeam');date=str(ref(data,b['gameDate'])).split(' ')[0]
   parsed=None
   for fmt in ['%m/%d/%y','%m/%d/%Y','%Y-%m-%d']:
    try:parsed=datetime.strptime(date[:10] if fmt=='%Y-%m-%d' else date,fmt).date();break
    except ValueError:continue
   if not parsed or hp is None or vp is None:continue
   if not 0<=hp<=hs or not 0<=vp<=vs or hp%2 or vp%2 or hp+vp==0:continue
   home=ref(data,b.get('thisTeamIsHomeTeam'))
   if home is not True and home is not False:continue
   return {'date':parsed.isoformat(),'points':hs if home else vs,'opponent_points':vs if home else hs,'paint_for':hp if home else vp,'paint_against':vp if home else hp,'format':'official whole-game SIDEARM totals'}
  except (KeyError,TypeError,ValueError):continue
 return None

def get(url,cache,audit):
 key=hashlib.sha256(url.encode()).hexdigest();p=cache/(key+'.html')
 if p.exists():return p.read_text()
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; BetWiseHistoricalResearch/1.0)','Accept':'text/html'})
  with urllib.request.urlopen(req,timeout=16) as response:
   body=response.read(7_000_000).decode('utf-8','replace')
  if len(body)<100:audit['empty_pages']+=1;return None
  p.write_text(body);return body
 except urllib.error.HTTPError as e:audit['http_'+str(e.code)]+=1;return None
 except Exception as e:audit['request_'+type(e).__name__]+=1;return None

def links(s,base,year):
 out=set();season=f'{year-1}-{str(year)[-2:]}'
 for value in re.findall(r'href=["\']([^"\']+)["\']',s):
  value=html.unescape(value);url=urljoin(base,value);p=urlsplit(url)
  if p.netloc!=urlsplit(base).netloc:continue
  if '/sports/mens-basketball/' in p.path and '/boxscore/' in p.path:
   m=re.search(r'/stats/([^/]+)/',p.path)
   if m and m[1] in [str(year-1),str(year),season,f'{year-1}-{year}']:out.add(url.split('#')[0])
  elif '/boxscore.aspx' in p.path.lower() and re.search(r'path=(mbball|mbb|m-baskbl)(?:&|$)',p.query,re.I):out.add(url.split('#')[0])
 return sorted(out)

def crawl(args):
 catalog=load(R/'data/cbb/official-paint-sources.json')['teams'];entries=sorted(catalog.items());entries=[x for i,x in enumerate(entries) if i%args.shards==args.shard]
 metrics=load(R/'data/cbb/opponent-metrics.json');registry=load(R/'data/sports/team-registry.json');byid={str(t['espn_id']):t['slug'] for t in registry['teams'] if t['sport']=='cbb'}
 archives={s:load(R/f'data/cbb/teams/{s}.json') for s in catalog};audit=Counter();progress=[];records={};lock=threading.Lock();cache=Path(args.cache_dir);cache.mkdir(parents=True,exist_ok=True)
 def school(pair):
  slug,config=pair;base=config['base_url'];local=Counter();found=[];attempted=0
  for year in range(2016,2027):
   season=archives[slug]['seasons'].get(str(year));expected={}
   if not season:continue
   for phase in season.get('phases',{}).values():
    for g in phase.get('games',[]):
     if g.get('status')!='final':continue
     day=datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
     expected.setdefault((day,g['points'],g['opponent_points']),{})[g['id']]=g
   if not expected:continue
   prior=metrics.get('seasons',{}).get(str(year),{}).get(slug,{})
   if prior.get('values',{}).get('Points in the Paint') is not None:continue
   attempted+=1;label=f'{year-1}-{str(year)[-2:]}';urls=[]
   for path in [f'/sports/mens-basketball/stats/{label}',f'/sports/mens-basketball/schedule/{label}']:
    page=get(base+path,cache,local)
    if page:urls+=links(page,base,year)
    if urls:break
   urls=sorted(set(urls));local['season_pages_attempted']+=1
   if not urls:local['seasons_without_box_links']+=1;continue
   for url in urls:
    body=get(url,cache,local)
    if not body:continue
    local['box_pages_read']+=1;box=parse_nuxt(body)
    if not box:local['unparsed_or_missing_paint']+=1;continue
    matches=expected.get((box['date'],box['points'],box['opponent_points']),{})
    if len(matches)!=1:local['date_score_mismatch']+=1;continue
    gid,g=next(iter(matches.items()));opp=byid.get(str(g.get('opponent_id')))
    record={**box,'year':str(year),'game_id':gid,'team':slug,'opponent':opp,'source':url}
    found.append(record);local['verified_team_games']+=1
    if opp:found.append({**record,'team':opp,'opponent':slug,'points':box['opponent_points'],'opponent_points':box['points'],'paint_for':box['paint_against'],'paint_against':box['paint_for']});local['verified_opponent_games']+=1
   time.sleep(.1)
  with lock:
   audit.update(local)
   for record in found:
    key=record['team']+'|'+record['game_id']
    if key not in records:records[key]=record
    elif (records[key]['paint_for'],records[key]['paint_against'])!=(record['paint_for'],record['paint_against']):audit['conflicting_official_values']+=1;records[key]['conflict']=True
   progress.append({'team':slug,'seasons_attempted':attempted,'verified_observations':len(found),**dict(local)})
   save(Path(args.output),{'shard':args.shard,'records':list(records.values()),'audit':dict(audit),'teams':progress})
   print(slug,'seasons',attempted,'observations',len(found),dict(local),flush=True)
 with ThreadPoolExecutor(max_workers=args.workers) as ex:
  futures=[ex.submit(school,pair) for pair in entries]
  for f in as_completed(futures):f.result()
 print('Shard finished',args.shard,len(records),dict(audit),flush=True)

def merge(args):
 paths=sorted(Path(args.input_dir).rglob('official-paint-shard-*.json'));assert len(paths)==args.shards,(len(paths),args.shards)
 existing=R/'data/cbb/official-paint-observations.json';records={}
 if existing.exists():records={(r['team'],r['game_id']):r for r in load(existing)['records']}
 audit=Counter();schools=[]
 for p in paths:
  d=load(p);audit.update(d['audit']);schools+=d['teams']
  for r in d['records']:
   key=r['team'],r['game_id']
   if key in records and (records[key].get('conflict') or (records[key]['paint_for'],records[key]['paint_against'])!=(r['paint_for'],r['paint_against'])):r['conflict']=True
   records[key]=r
 metrics=load(R/'data/cbb/opponent-metrics.json');groups=defaultdict(dict);byyear=Counter();gaps=[]
 for r in records.values():
  if not r.get('conflict'):groups[r['year'],r['team']][r['game_id']]=r
 for slug in load(R/'data/cbb/official-paint-sources.json')['teams']:
  archive=load(R/f'data/cbb/teams/{slug}.json')
  for year,season in archive['seasons'].items():
   games={g['id']:g for g in season.get('phases',{}).get('regular',{}).get('games',[]) if g.get('status')=='final'}
   if not games:continue
   samples=[r for gid,r in groups.get((year,slug),{}).items() if gid in games and r['points']==games[gid]['points'] and r['opponent_points']==games[gid]['opponent_points']];n=len(samples)
   entry=metrics['seasons'].setdefault(year,{}).setdefault(slug,{'values':{},'ranks':{}})
   if n<10 or n/len(games)<.95:
    # A newly discovered conflict must also invalidate an earlier official
    # aggregate if the remaining verified sample no longer meets coverage.
    for key in ['Points in the Paint','Points in the Paint Allowed']:
     sample=entry.get('metric_samples',{}).get(key,{})
     if sample.get('method','').startswith('Official'):
      entry.get('values',{}).pop(key,None);entry.get('ranks',{}).pop(key,None);entry.get('metric_samples',{}).pop(key,None)
    if entry['values'].get('Points in the Paint') is None:gaps.append({'team':slug,'season':year,'official_games':n,'expected_games':len(games)})
    continue
   prior_sample=entry.get('metric_samples',{}).get('Points in the Paint',{})
   prior=prior_sample.get('games',0)
   if entry['values'].get('Points in the Paint') is not None and n<prior and not prior_sample.get('method','').startswith('Official'):continue
   vals={'Points in the Paint':sum(r['paint_for'] for r in samples)/n,'Points in the Paint Allowed':sum(r['paint_against'] for r in samples)/n}
   sources=sorted({r['source'] for r in samples});entry['values'].update(vals)
   for key in vals:entry.setdefault('metric_samples',{})[key]={'games':n,'expected_games':len(games),'source':sources[0],'sources':sources,'method':'Official whole-game box totals; exact school, date and final-score match'}
   byyear[year]+=1
 for year,teams in metrics['seasons'].items():
  for key,desc in [('Points in the Paint',True),('Points in the Paint Allowed',False)]:
   pairs=sorted([(s,t['values'][key]) for s,t in teams.items() if t.get('values',{}).get(key) is not None],key=lambda x:x[1],reverse=desc);last=None;rank=0
   for i,(s,v) in enumerate(pairs):
    if v!=last:rank=i+1
    teams[s].setdefault('ranks',{})[key]={'rank':rank,'size':len(pairs)};last=v
 save(existing,{'records':list(records.values())});save(R/'data/cbb/opponent-metrics.json',metrics)
 report={'schools_attempted':len(schools),'verified_official_team_game_observations':len(records),'published_team_seasons_by_year':dict(byyear),'audit':dict(audit),'remaining_unfilled_team_seasons':gaps,'schools':schools}
 save(R/'data/cbb/official-paint-backfill-report.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['schools','remaining_unfilled_team_seasons']}),flush=True);print('Remaining unfilled:',len(gaps),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--merge',action='store_true');p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=12);p.add_argument('--workers',type=int,default=5);p.add_argument('--cache-dir',default='/tmp/cbb-official-paint-cache');p.add_argument('--output',default='/tmp/official-paint-shard-0.json');p.add_argument('--input-dir',default='/tmp/official-paint-shards');args=p.parse_args();merge(args) if args.merge else crawl(args)
