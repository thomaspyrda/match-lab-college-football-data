"""Fill missing CBB markets only, using exact archived game identities/scores.

SBR observations retain original workbook checksums and source row identities.
ESPN core odds are checked against the completed event summary before staging.
Existing markets are never replaced. No predicted or inferred betting lines.
"""
import argparse,json,re,math,gzip,urllib.request,time
from pathlib import Path
from collections import defaultdict,Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
from datetime import datetime
from zoneinfo import ZoneInfo
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n')
def day(g):return datetime.fromisoformat(g['date'].replace('Z','+00:00')).astimezone(ZoneInfo('America/New_York')).date().isoformat()
def played(g):return g.get('status')=='final' and isinstance(g.get('points'),(int,float)) and isinstance(g.get('opponent_points'),(int,float)) and g['points']+g['opponent_points']>2
def has(g,k):return (g.get(k) if g.get(k) is not None else g.get(k+'_result')) in (['W','L','P'] if k=='ats' else ['O','U','P'])
def valid(v,lo,hi):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) and lo<=v<=hi and v*2==int(v*2)
def context():
 teams=[t for t in read(R/'data/sports/team-registry.json')['teams'] if t['sport']=='cbb'];ids={str(t['espn_id']):t['slug'] for t in teams};rev={v:k for k,v in ids.items()};archives={t['slug']:read(R/f"data/cbb/teams/{t['slug']}.json") for t in teams};markets={s:read(R/f'data/cbb/markets/{s}.json') for s in archives};games={};group=defaultdict(dict)
 for s,a in archives.items():
  for y,se in a['seasons'].items():
   if not 2016<=int(y)<=2026:continue
   for phase in se.get('phases',{}).values():
    for g in phase.get('games',[]):
     if not played(g):continue
     gid=str(g['id']);opp=ids.get(str(g.get('opponent_id')))
     games[s,y,gid]=g
     if opp:group[y,gid][s]={'team':s,'opponent':opp,'team_id':rev[s],'opponent_id':rev[opp],'year':y,'game_id':gid,'date':day(g),'points':g['points'],'opponent_points':g['opponent_points']}
 targets={}
 for key,sides in group.items():
  if len(sides)!=2:continue
  a,b=list(sides.values())
  if a['points']!=b['opponent_points'] or b['points']!=a['opponent_points'] or a['date']!=b['date']:continue
  if any(not has({**games[s,key[0],key[1]],**markets[s].get('games',{}).get(key[0],{}).get(key[1],{})},k) for s in sides for k in ['ats','ou']):targets[key]=list(sides.values())
 return archives,markets,games,targets
def get(url):
 for attempt in range(2):
  try:
   req=urllib.request.Request(url,headers={'Accept-Encoding':'gzip','User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(req,timeout=20) as r:
    b=r.read();b=gzip.decompress(b) if r.headers.get('Content-Encoding')=='gzip' else b
   return json.loads(b)
  except Exception:
   if attempt:raise
   time.sleep(.3)
def scan(args):
 _,_,_,targets=context();work=[x for i,x in enumerate(sorted(targets.items())) if i%args.shards==args.shard];audit=Counter();records=[]
 def one(pair):
  (y,gid),sides=pair;local=Counter();url=f'https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball/events/{gid}/competitions/{gid}/odds?limit=100'
  try:items=get(url).get('items',[])
  except Exception as e:return [],{'request_'+type(e).__name__:1}
  picks={};wanted={r['team_id'] for r in sides}
  for item in sorted(items,key=lambda v:({'consensus':0,'teamrankings':1,'numberfire':2}.get(v.get('provider',{}).get('name','').lower(),3),v.get('provider',{}).get('priority',999),v.get('provider',{}).get('name',''))):
   def team_id(k):
    m=re.search(r'/teams/(\d+)',item.get(k,{}).get('team',{}).get('$ref',''));return m[1] if m else str(item.get(k,{}).get('teamId',''))
   away,home=team_id('awayTeamOdds'),team_id('homeTeamOdds')
   if {away,home}!=wanted:continue
   a,h=item.get('awayTeamOdds',{}),item.get('homeTeamOdds',{});spread=item.get('spread');total=item.get('overUnder');provider=item.get('provider',{}).get('name','ESPN archived provider')
   if 'ats' not in picks and valid(spread,-60,60):
    magnitude=abs(spread);awayline=None
    if magnitude==0 and str(item.get('details','')).strip().upper() in ['EVEN','PK','PICK','PICKEM']:awayline=0
    elif magnitude and a.get('favorite') is True and h.get('favorite') is False:awayline=-magnitude
    elif magnitude and h.get('favorite') is True and a.get('favorite') is False:awayline=magnitude
    if awayline is not None:picks['ats']=(away,awayline,provider)
   if 'ou' not in picks and valid(total,60,350):picks['ou']=(None,total,provider)
  if not picks:return [],{'no_valid_market':1}
  # The odds collection itself has no final scores. Check the linked completed
  # game summary before accepting any market, including provider team identities.
  try:
   summary=get(f'https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/summary?event={gid}');header=summary['header'];comp=next(c for c in header['competitions'] if str(c['id'])==gid)
   scores={str(c['team']['id']):int(c['score']) for c in comp['competitors']}
   if not comp.get('status',{}).get('type',{}).get('completed') or set(scores)!=wanted or day({'date':comp['date']})!=sides[0]['date'] or any(scores[r['team_id']]!=r['points'] for r in sides):return [],{'summary_mismatch':1}
  except Exception as e:return [],{'summary_'+type(e).__name__:1}
  out=[]
  for r in sides:
   v={**r,'source':url,'line_type':'ESPN archived provider line'}
   if 'ats' in picks:
    away,line,provider=picks['ats'];v.update(spread=line if r['team_id']==away else -line,ats_provider=provider)
   if 'ou' in picks:v.update(total=picks['ou'][1],ou_provider=picks['ou'][2])
   out.append(v)
  return out,{'verified_market_games':1}
 with ThreadPoolExecutor(args.workers) as pool:
  for i,f in enumerate(as_completed([pool.submit(one,p) for p in work]),1):
   rr,aa=f.result();records+=rr;audit.update(aa)
   if i%25==0:save(Path(args.output),{'records':records,'audit':dict(audit),'target_games':len(work),'processed':i});print(args.shard,i,'/',len(work),dict(audit),flush=True)
 save(Path(args.output),{'records':records,'audit':dict(audit),'target_games':len(work),'processed':len(work)});print('Completed',args.shard,dict(audit),flush=True)
 if len(work)>20 and sum(v for k,v in audit.items() if k.startswith('request_'))>.9*len(work):raise RuntimeError('Odds archive requests failed; this is not evidence that lines are unavailable')
def apply(args):
 archives,markets,games,targets=context();before=len(targets);observations=[];source_audit=Counter();sbr=read(R/'data/cbb/sbr-market-recovery-observations.json')
 if args.sbr:
  from urllib.parse import quote
  for r in sbr['records']:
   info=sbr['files'][str(r['source_year'])];observations.append({**r,'source':f"https://github.com/{sbr['mirror_repository']}/blob/{sbr['mirror_commit']}/"+quote(info['mirror_path']),'line_type':'Sportsbook Reviews Online archived closing line','ats_provider':'SBR archived close','ou_provider':'SBR archived close','workbook_sha256':info['sha256']})
 if args.input_dir:
  files=sorted(Path(args.input_dir).rglob('markets-shard-*.json'));assert len(files)==args.shards,(len(files),args.shards)
  for p in files:
   d=read(p);assert d['processed']==d['target_games'];observations+=d['records'];source_audit.update(d['audit'])
 count=Counter();changed=set();recovered=defaultdict(set)
 for r in observations:
  s,y,gid=r['team'],r['year'],str(r['game_id']);g=games.get((s,y,gid))
  if not g or day(g)!=r['date'] or g['points']!=r['points'] or g['opponent_points']!=r['opponent_points']:raise ValueError('Observation does not match archive')
  if r.get('opponent') not in archives or str(g.get('opponent_id'))!=str(archives[r['opponent']]['team_id']):raise ValueError('Archived opponent identity mismatch')
  if r.get('opponent_id') and str(g.get('opponent_id'))!=r['opponent_id']:raise ValueError('Opponent mismatch')
  out=markets[s].setdefault('games',{}).setdefault(y,{}).setdefault(gid,{})
  for k,field,lo,hi in [('ats','spread',-60,60),('ou','total',60,350)]:
   if has({**g,**out},k) or not valid(r.get(field),lo,hi):continue
   v=r[field];margin=g['points']-g['opponent_points']+v if k=='ats' else g['points']+g['opponent_points']-v;result=('W' if margin>0 else 'L' if margin<0 else 'P') if k=='ats' else ('O' if margin>0 else 'U' if margin<0 else 'P')
   out.update({field:v,k:result,k+'_source':r['source'],k+'_provider':r.get(k+'_provider','Archived source')});out.setdefault('source',r['source']);out.setdefault('line_type',r['line_type']);out.setdefault('market_line_types',{})[k]=r['line_type']
   count[k+'_team_rows']+=1;recovered[k].add(gid);recovered['any'].add(gid);changed.add((s,y))
 for s,y in changed:
  seen=set();ats=[0,0,0];ou=[0,0,0]
  for phase in archives[s]['seasons'][y].get('phases',{}).values():
   for g in phase.get('games',[]):
    gid=str(g['id'])
    if not played(g) or gid in seen:continue
    seen.add(gid);v={**g,**markets[s]['games'].get(y,{}).get(gid,{})}
    if has(v,'ats'):ats[['W','L','P'].index(v.get('ats') or v.get('ats_result'))]+=1
    if has(v,'ou'):ou[['O','U','P'].index(v.get('ou') or v.get('ou_result'))]+=1
  rec={'ats':ats,'ou':ou,'expected_games':len(seen),'source':'https://github.com/thomaspyrda/match-lab-college-football-data/blob/main/data/cbb/historical-market-recovery-report.json','coverage':'Computed from verified archived game lines, including postseason; unlined games excluded'};markets[s].setdefault('verified_game_seasons',{})[y]=rec;old=markets[s].get('seasons',{}).get(y)
  if not old or sum(ats)>=sum(old['ats']) and sum(ou)>=sum(old['ou']) and (sum(ats)>sum(old['ats']) or sum(ou)>sum(old['ou'])):markets[s].setdefault('seasons',{})[y]=rec;count['season_summaries_updated']+=1
 for s in {s for s,y in changed}:save(R/f'data/cbb/markets/{s}.json',markets[s])
 if args.sbr and not changed:print('SBR observations already applied',flush=True);return
 _,_,_,remaining=context();path=R/'data/cbb/historical-market-recovery-report.json';history=read(path).get('passes',[]) if path.exists() else []
 record={'method':'Missing markets only; exact two archived teams, Eastern game date, both final scores; no market imputation','source':'SBR original workbook archival mirror' if args.sbr else 'ESPN archived provider odds plus completed event summary','target_games_before':before,'target_games_after':len(remaining),'unique_games_with_added_markets':len(recovered['any']),'unique_games_with_added_ats':len(recovered['ats']),'unique_games_with_added_ou':len(recovered['ou']),'counts':dict(count),'source_audit':dict(source_audit)};history.append(record);save(path,{'passes':history});print(json.dumps(record),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--scan',action='store_true');p.add_argument('--sbr',action='store_true');p.add_argument('--shard',type=int,default=0);p.add_argument('--shards',type=int,default=12);p.add_argument('--workers',type=int,default=5);p.add_argument('--input-dir');p.add_argument('--output',default='/tmp/markets-shard-0.json');args=p.parse_args();scan(args) if args.scan else apply(args)
