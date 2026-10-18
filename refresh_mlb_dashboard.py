#!/usr/bin/env python3
"""Current MLB matchup snapshots. Explicit phase, observed totals, no completed-game backtests."""
from dashboard_snapshot import compact
import json, time, urllib.request, unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
API='https://site.api.espn.com/apis/site/v2/sports/baseball/mlb/'
UTC=timezone.utc

def get(path,optional=False):
 for attempt in range(3):
  try:
   with urllib.request.urlopen(API+path,timeout=25) as r:return json.load(r)
  except urllib.error.HTTPError as e:
   if optional and e.code==404:return {}
   if attempt==2:raise
  except Exception:
   if attempt==2:raise
  time.sleep(attempt+1)

def stamp(s):return datetime.fromisoformat(s.replace('Z','+00:00'))
def ratio(a,b,scale=1):return a/b*scale if a is not None and b else None

def categories(d,year,phase):
 requested=d.get('requestedSeason',d.get('season',{}))
 if requested.get('year')!=year or requested.get('type')!=phase:return {}
 return {c['name']:{s['name']:s.get('value') for s in c['stats']} for c in d.get('results',{}).get('stats',{}).get('categories',[])}

METRICS=[('rpg','Runs per game','OFFENSE',True,'','Runs scored / games played.'),('rapg','Runs allowed per game','DEFENSE',False,'','Runs allowed / games played.'),('avg','Batting average','OFFENSE',True,'decimal','Hits / at-bats.'),('baa','Batting average allowed','DEFENSE',False,'decimal','Opponent hits / opponent at-bats.'),('obp','On-base percentage','OFFENSE',True,'decimal','Source-reported on-base percentage.'),('opp_obp','On-base percentage allowed','DEFENSE',False,'decimal','Opponent on-base percentage.'),('slg','Slugging percentage','OFFENSE',True,'decimal','Total bases / at-bats.'),('opp_slg','Slugging percentage allowed','DEFENSE',False,'decimal','Opponent total bases / at-bats.'),('ops','OPS','OFFENSE',True,'decimal','On-base plus slugging percentage.'),('opp_ops','OPS allowed','DEFENSE',False,'decimal','Opponent on-base plus slugging percentage.'),('k_rate','Strikeout rate','OFFENSE',False,'%','Batting strikeouts / plate appearances.'),('k9','Strikeouts per 9 innings','DEFENSE',True,'','Pitching strikeouts per nine innings.'),('bb_rate','Walk rate','OFFENSE',True,'%','Batting walks / plate appearances.'),('whip','WHIP','DEFENSE',False,'','Walks plus hits per inning pitched.'),('hrpg','Home runs per game','OFFENSE',True,'','Home runs / games played.'),('era','ERA','DEFENSE',False,'','Earned runs per nine innings.')]

def profile(c):
 b=c.get('batting',{});p=c.get('pitching',{});n=b.get('teamGamesPlayed',0)
 m={'rpg':ratio(b.get('runs'),n),'rapg':ratio(p.get('runs'),n),'avg':b.get('avg'),'baa':p.get('opponentAvg'),'obp':b.get('onBasePct'),'opp_obp':p.get('opponentOnBasePct'),'slg':b.get('slugAvg'),'opp_slg':p.get('opponentSlugAvg'),'ops':b.get('OPS'),'opp_ops':p.get('opponentOPS'),'k_rate':ratio(b.get('strikeouts'),b.get('plateAppearances'),100),'k9':p.get('strikeoutsPerNineInnings'),'bb_rate':ratio(b.get('walks'),b.get('plateAppearances'),100),'whip':p.get('WHIP'),'hrpg':ratio(b.get('homeRuns'),n),'era':p.get('ERA')}
 if not n:m={k:None for k in m}
 return {'games':int(n),'record':f"{int(p['wins'])}–{int(p['losses'])}" if n and 'wins' in p and 'losses' in p else '—','ppg':m['rpg'],'allowed':m['rapg'],'metrics':m,'results':[],'players':[],'last_game_date':None,'last5_market':{'ats':{'lined_games':0,'wins':0,'losses':0,'pushes':0},'ou':{'lined_games':0,'overs':0,'unders':0,'pushes':0},'window_games':0}}

def ranking(profiles,key,high):
 values=[(i,p['metrics'].get(key)) for i,p in profiles.items() if p['metrics'].get(key) is not None]
 return {i:{'value':v,'rank':1+sum(x>v if high else x<v for _,x in values),'population':len(values),'percentile':100*sum(x<v if high else x>v for _,x in values)/max(1,len(values)-1)} for i,v in values}

def roster(i):
 d=get('teams/'+i+'/roster',True);out=[]
 for group in d.get('athletes',[]):
  for a in group.get('items',[group] if 'id' in group else []):
   out.append({'id':'mlb:espn:player:'+a['id'],'name':a.get('displayName',a.get('fullName')),'jersey':a.get('jersey','—'),'position':a.get('position',{}).get('abbreviation',group.get('position','—')),'bats':a.get('bats',{}).get('displayValue','—'),'throws':a.get('throws',{}).get('displayValue','—'),'status':a.get('status',{}).get('name','Not reported'),'source':'https://www.espn.com/mlb/player/_/id/'+a['id']})
 return i,out

def game_lineups(event_id, allowed_ids):
 """Use only nine explicitly marked starters, never the complete roster."""
 data=get('summary?event='+str(event_id),True)
 result={}
 for side in (data.get('boxscore') or {}).get('players',[]):
  tid=str((side.get('team') or {}).get('id',''))
  if tid not in allowed_ids:continue
  candidates=[]
  for group in side.get('statistics',[]):
   for entry in group.get('athletes',[]):
    athlete=entry.get('athlete') or {}
    role=(athlete.get('position') or {}).get('abbreviation','')
    if entry.get('starter') is not True or role in ('P','SP','RP','CL'):continue
    if not athlete.get('id'):continue
    candidates.append({'name':athlete.get('displayName',athlete.get('fullName','')),
      'position':role,'source':'https://www.espn.com/mlb/player/_/id/'+str(athlete['id'])})
  unique=list({c['source']:c for c in candidates}.values())
  if len(unique)==9:result[tid]=unique
 return result

def season_player_stats(slug,year):
 path=ROOT/'data'/'mlb'/'historical-players'/(slug+'.json')
 if not path.exists():return {}
 try:
  rows=json.loads(path.read_text()).get('years',{}).get(str(year),{})
  return {''.join(c for c in p['name'].lower() if c.isalnum()):p
          for group in ('hitters','starters','relievers') for p in rows.get(group,[]) if p.get('name')}
 except (OSError,ValueError,KeyError,TypeError):return {}

def official_probables(events):
 """Read MLB official probable pitchers for upcoming games, keyed by day and team name."""
 if not events:return {}
 try:
  dates=[stamp(e['date']).date().isoformat() for e in events]
  url=('https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate='+
        min(dates)+'&endDate='+max(dates)+'&gameTypes=R,F,D,L,W&hydrate=probablePitcher')
  with urllib.request.urlopen(url,timeout=25) as response:payload=json.load(response)
  output={}
  for day in payload.get('dates',[]):
   for game in day.get('games',[]):
    official_date=game.get('officialDate') or str(game.get('gameDate',''))[:10]
    for side in ('away','home'):
     entry=game.get('teams',{}).get(side,{})
     pitcher=entry.get('probablePitcher') or {}
     team=entry.get('team') or {}
     if pitcher.get('fullName') and team.get('name'):
      output[(official_date,team['name'].casefold())]=pitcher['fullName']
  return output
 except Exception as error:
  print('Official probable-pitcher lookup unavailable:',type(error).__name__)
  return {}

def player_key(name):
 text=unicodedata.normalize('NFKD',name or '')
 return ''.join(ch for ch in text.lower() if ch.isalnum())

def current_phase_player_stats(espn_teams,year,phase):
 """Add phase-specific player counting stats; recompute rates, without mixing regular season."""
 game_types=('R',) if phase==2 else ('F','D','L','W') if phase==3 else ('S',)
 prefix='https://statsapi.mlb.com/api/v1/'
 def fetch_json(route):
  with urllib.request.urlopen(prefix+route,timeout=30) as response:
   return json.load(response)
 official=fetch_json('teams?sportId=1&season='+str(year)).get('teams',[])
 lookup={team['name'].casefold():str(team['id']) for team in official}
 def query(entry):
  tid,team=entry
  mlb_id=lookup.get(team['name'].casefold())
  if not mlb_id:return tid,{}
  players={}
  for group in ('hitting','pitching'):
   for game_type in game_types:
    route=('stats?stats=season&group='+group+'&season='+str(year)+
           '&teamId='+mlb_id+'&playerPool=ALL&limit=1000&gameType='+game_type)
    data=fetch_json(route)
    for block in data.get('stats',[]):
     for split in block.get('splits',[]):
      if str((split.get('team') or {}).get('id'))!=mlb_id:continue
      player=split.get('player') or {};stat=split.get('stat') or {}
      key=player_key(player.get('fullName',''))
      if not key or not stat:continue
      row=players.setdefault(key,{'name':player.get('fullName'),'mlb_id':player.get('id'),'_h':{},'_p':{}})
      section=row['_h' if group=='hitting' else '_p']
      fields=(('atBats','hits','runs','homeRuns','rbi','baseOnBalls','hitByPitch',
              'sacFlies','totalBases','doubles','triples') if group=='hitting' else
              ('gamesPlayed','gamesStarted','earnedRuns','hits','baseOnBalls','strikeOuts'))
      for field in fields:
       raw=stat.get(field)
       if raw is not None:
        section[field]=section.get(field,0)+int(raw)
      if group=='pitching' and stat.get('inningsPitched') is not None:
       whole,_,partial=str(stat['inningsPitched']).partition('.')
       if partial not in ('','0','1','2'):
        raise ValueError('Invalid pitching thirds '+str(stat['inningsPitched']))
       section['_outs']=section.get('_outs',0)+int(whole)*3+int(partial or 0)
  result={}
  for key,row in players.items():
   h,p=row['_h'],row['_p']
   out={'name':row['name'],'mlb_id':row.get('mlb_id')}
   if h:
    ab=h.get('atBats',0);hits=h.get('hits',0)
    walks=h.get('baseOnBalls',0);hbp=h.get('hitByPitch',0);sf=h.get('sacFlies',0)
    tb=h.get('totalBases')
    if tb is None:
     tb=hits+h.get('doubles',0)+2*h.get('triples',0)+3*h.get('homeRuns',0)
    denom=ab+walks+hbp+sf
    obp=(hits+walks+hbp)/denom if denom else None
    out.update({'ab':ab,'r':h.get('runs'),'hr':h.get('homeRuns'),
                'rbi':h.get('rbi'),'avg':hits/ab if ab else None,
                'obp':obp,'ops':obp+tb/ab if obp is not None and ab else None})
   if p:
    outs=p.get('_outs',0);innings=outs/3
    out.update({'gp':p.get('gamesPlayed'),'gs':p.get('gamesStarted'),
                'ip':str(outs//3)+'.'+str(outs%3),
                'era':9*p.get('earnedRuns',0)/innings if innings else None,
                'whip':(p.get('hits',0)+p.get('baseOnBalls',0))/innings if innings else None,
                'so':p.get('strikeOuts')})
   result[key]=out
  person_ids=[str(row['mlb_id']) for row in result.values() if row.get('mlb_id')]
  for start in range(0,len(person_ids),100):
   people=fetch_json('people?personIds='+','.join(person_ids[start:start+100])).get('people',[])
   for person in people:
    key=player_key(person.get('fullName'))
    if key not in result:continue
    result[key]['bats']=((person.get('batSide') or {}).get('code') or '').upper()
    result[key]['throws']=((person.get('pitchHand') or {}).get('code') or '').upper()
  return tid,result
 # Raise errors rather than silently storing an apparently valid empty snapshot.
 return dict(ThreadPoolExecutor(5).map(query,espn_teams.items()))


def main():
 now=datetime.now(UTC);today=now.astimezone(ZoneInfo('America/New_York')).date();year=today.year
 teams={str(t['espn_id']):t for t in json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'] if t['sport']=='mlb'}
 assert len(teams)==30
 dates=[today+timedelta(days=i) for i in range(-8,8)]
 boards=list(ThreadPoolExecutor(8).map(lambda d:get('scoreboard?limit=1000&dates='+d.strftime('%Y%m%d')),dates))
 events={e['id']:e for board in boards for e in board.get('events',[]) if all(c['team']['id'] in teams for c in e['competitions'][0]['competitors'])}
 upcoming=sorted([e for e in events.values() if not e['status']['type'].get('completed') and stamp(e['date'])>=now-timedelta(hours=8)],key=lambda e:e['date'])
 phase=upcoming[0]['season']['type'] if upcoming else (3 if today.month>=10 else 2)
 upcoming=[e for e in upcoming if e['season']['type']==phase]
 def stats(i):return i,profile(categories(get(f'teams/{i}/statistics?season={year}&seasontype={phase}',True),year,phase))
 profiles=dict(ThreadPoolExecutor(8).map(stats,teams))
 past=sorted([e for e in events.values() if e['status']['type'].get('completed') and e['season']['type']==phase and stamp(e['date'])<=now],key=lambda e:e['date'])
 for i,p in profiles.items():
  for e in past:
   comp=e['competitions'][0];own=next((c for c in comp['competitors'] if c['team']['id']==i),None)
   if not own:continue
   opp=next(c for c in comp['competitors'] if c is not own);a=float(own['score']);b=float(opp['score'])
   p['results'].append({'date':e['date'],'result':'W' if a>b else 'L','score':f'{int(a)}–{int(b)}','location':'Neutral' if comp.get('neutralSite') else own['homeAway'].title()})
  p['results']=p['results'][-5:];p['last_game_date']=p['results'][-1]['date'] if p['results'] else None;p['last5_market']['window_games']=len(p['results'])
 # Source historical market quotes separately; never infer missing lines.
 def historical_line(e):
  d=get('summary?event='+e['id'],True);quotes=d.get('pickcenter',[])
  return e['id'],quotes[0] if quotes else {}
 lines=dict(ThreadPoolExecutor(8).map(historical_line,past))
 for i,p in profiles.items():
  games=[e for e in past if any(c['team']['id']==i for c in e['competitions'][0]['competitors'])][-5:]
  for e in games:
   quote=lines.get(e['id'],{});comp=e['competitions'][0];own=next(c for c in comp['competitors'] if c['team']['id']==i);opp=next(c for c in comp['competitors'] if c is not own)
   a=float(own['score']);b=float(opp['score']);total=quote.get('overUnder');spread=quote.get('spread')
   if total is not None:
    margin=a+b-float(total);r=p['last5_market']['ou'];r['lined_games']+=1;r['overs' if margin>0 else 'unders' if margin<0 else 'pushes']+=1
   homefav=quote.get('homeTeamOdds',{}).get('favorite');awayfav=quote.get('awayTeamOdds',{}).get('favorite')
   if spread is not None and (homefav or awayfav):
    home_spread=-abs(float(spread)) if homefav else abs(float(spread));margin=a-b+(home_spread if own['homeAway']=='home' else -home_spread)
    r=p['last5_market']['ats'];r['lined_games']+=1;r['wins' if margin>0 else 'losses' if margin<0 else 'pushes']+=1
 ids={c['team']['id'] for e in upcoming for c in e['competitions'][0]['competitors']};out=[]
 player_stats=current_phase_player_stats({tid:teams[tid] for tid in ids},year,phase)
 def lineup_for(e):
  allowed={c['team']['id'] for c in e['competitions'][0]['competitors']}
  return e['id'],game_lineups(e['id'],allowed)
 lineups=dict(ThreadPoolExecutor(6).map(lineup_for,upcoming))
 # Use the latest confirmed lineup only as a labeled reference when today's lineup is unavailable.
 latest_lineups={}
 recent_events=list(reversed(past))
 def recent_lineup(e):
  allowed={c['team']['id'] for c in e['competitions'][0]['competitors']}
  return e['id'],game_lineups(e['id'],allowed)
 for event_id, found in ThreadPoolExecutor(6).map(recent_lineup,recent_events[:18]):
  for team_id, players in found.items():
   if team_id not in latest_lineups:
    prior=next((ev for ev in recent_events if ev['id']==event_id),None)
    latest_lineups[team_id]={'players':players,'date':prior['date'] if prior else None}
 def stat_for(team_id,person):
  key=player_key(person['name'])
  return player_stats.get(team_id,{}).get(key,{})
 official_starters=official_probables(upcoming)
 # Source-reviewed matchup fallback only when the official feed omits announced probables.
 # Restricted to the exact 2026-10-18 Rays/Guardians game; never extrapolate.
 for e in upcoming:
  match={str(c['team']['id']) for c in e['competitions'][0]['competitors']}
  if stamp(e['date']).astimezone(ZoneInfo('America/New_York')).date().isoformat()=='2026-10-18' and match=={'30','5'}:
   official_starters.setdefault(('2026-10-18','tampa bay rays'),'Drew Rasmussen')
   official_starters.setdefault(('2026-10-18','cleveland guardians'),'Parker Messick')

 ranks={key:ranking(profiles,key,high) for key,_,_,high,_,_ in METRICS}
 for e in upcoming:
  comp=e['competitions'][0];sides={c['homeAway']:c for c in comp['competitors']};a=sides['away']['team']['id'];h=sides['home']['team']['id']
  def team(i):
   t=teams[i];c=sides['away' if i==a else 'home'];return {'id':i,'team_id':t['id'],'name':t['name'],'abbr':t['abbreviation'],'logo':t['logo'],'color':'#'+c['team'].get('color','666666'),'profile':profiles[i],'lineup':[{**p,'stats':stat_for(i,p)} for p in (lineups.get(e['id'],{}).get(i,[]) or latest_lineups.get(i,{}).get('players',[]))],'lineup_status':'Announced' if len(lineups.get(e['id'],{}).get(i,[]))==9 else 'Recent confirmed lineup (not today)' if i in latest_lineups else 'Not announced','lineup_reference_date':latest_lineups.get(i,{}).get('date') if not lineups.get(e['id'],{}).get(i,[]) else None,'probable':official_starters.get((stamp(e['date']).date().isoformat(),t['name'].casefold())) or next((x['athlete']['displayName'] for x in c.get('probables',[]) if x.get('athlete')),None),'probable_stats':player_stats.get(i,{}).get(player_key(official_starters.get((stamp(e['date']).date().isoformat(),t['name'].casefold())) or next((x['athlete']['displayName'] for x in c.get('probables',[]) if x.get('athlete')),'')),{}),'relievers':sorted([p for p in player_stats.get(i,{}).values() if p.get('gp') is not None and (p.get('gp') or 0)>(p.get('gs') or 0) and player_key(p.get('name'))!=player_key(official_starters.get((stamp(e['date']).date().isoformat(),t['name'].casefold())) or '')],key=lambda p:(-((p.get('gp') or 0)-(p.get('gs') or 0)),-(p.get('so') or 0),p.get('name','')))[:5]}
  odds=comp.get('odds',[]);line=odds[0] if odds else {};tip=stamp(e['date'])
  out.append({'id':e['id'],'date':e['date'],'label':tip.astimezone(ZoneInfo('America/New_York')).strftime('%a %b %-d · %-I:%M %p ET'),'status':e['status']['type']['description'],'away':team(a),'home':team(h),'metrics':[{'key':k,'label':label,'unit':unit,'high':high,'suffix':suffix,'note':note,'away':ranks[k].get(a),'home':ranks[k].get(h)} for k,label,unit,high,suffix,note in METRICS],'venue':comp.get('venue',{}).get('fullName','Venue unavailable'),'neutral':comp.get('neutralSite',False),'market':{'spread':line.get('details'),'total':line.get('overUnder'),'provider':line.get('provider',{}).get('name'),'observed_at':now.isoformat() if line else None},'source':'https://www.espn.com/mlb/game/_/gameId/'+e['id'],'profile_cutoff':now.isoformat()})
 data={'schema_version':1,'season':str(year),'season_type':{1:'Preseason',2:'Regular season',3:'Postseason'}[phase],'updated_at':now.isoformat(),'completed_games':len(past),'games':out,'coverage':{'refresh':'Hourly snapshot, not a live scoreboard'},'methodology':'Current ESPN season totals in the selected season type. Rankings include only teams with a completed sample; postseason and regular season are never combined. Upcoming games only; these snapshots are not historical pregame profiles. Recent form uses observed final results in the last eight calendar days, up to five games. Run-line and total records use available ESPN published historical quotes; missing lines are excluded and closing status is not independently verified.'}
 dest=ROOT/'mlb/dashboard/data/dashboard.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(data,separators=(',',':'))+'\n');print(f"MLB {data['season_type']}: {len(out)} upcoming matchups, {len(past)} recent final games, {sum(p['games']>0 for p in profiles.values())} ranked teams")
if __name__=='__main__':main()
