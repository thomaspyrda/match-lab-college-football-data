"""Collect sourced CFB leadership, recruiting, season metrics and player leaders."""
import json, os, time, urllib.parse, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
ALIASES={'UConn':'Connecticut','Ole Miss':'Mississippi','UTSA':'Texas-San Antonio','Appalachian State':'App State','FIU':'Florida International','San Jose State':'San José State','Miami (FL)':'Miami','Miami (OH)':'Miami (OH)','Hawaii':"Hawai'i",'UMass':'Massachusetts','Louisiana-Lafayette':'Louisiana'}
def canon(name):return ALIASES.get(name,name)
def num(v):
 try:return float(v) if v is not None and v!='' else None
 except (ValueError,TypeError):return None
def api(path,**params):
 key=os.environ.get('CFBD_API_KEY')
 if not key:raise RuntimeError('CFBD_API_KEY is required')
 url='https://api.collegefootballdata.com'+path+'?'+urllib.parse.urlencode(params)
 request=urllib.request.Request(url,headers={'Authorization':'Bearer '+key,'Accept':'application/json','User-Agent':'BetWiseTeamHistory/1.0'})
 for attempt in range(3):
  try:
   with urllib.request.urlopen(request,timeout=90) as response:return json.load(response),url
  except Exception:
   if attempt==2:raise
   time.sleep(2**attempt)

FIELDS={
 'passing':[('passing_yards',['passing:YDS']),('passing_tds',['passing:TD']),('interceptions',['passing:INT']),('attempts',['passing:ATT','passing:ATTEMPTS']),('completions',['passing:COMPLETIONS','passing:CMP','passing:COMP'])],
 'rushing':[('rushing_yards',['rushing:YDS']),('rushing_tds',['rushing:TD']),('carries',['rushing:CAR','rushing:ATT','rushing:CARRIES'])],
 'receiving':[('receiving_yards',['receiving:YDS']),('receiving_tds',['receiving:TD']),('receptions',['receiving:REC'])],
 'defense':[('combined_tackles',['defensive:TOT','defensive:TOTAL','defensive:TACKLES']),('solo_tackles',['defensive:SOLO']),('assists',['defensive:AST']),('sacks',['defensive:SACKS','defensive:SACK']),('tfl',['defensive:TFL']),('qb_hits',['defensive:QB HUR','defensive:QB_HUR']),('passes_defended',['defensive:PD']),('def_interceptions',['interceptions:INT','defensive:INT']),('interception_yards',['interceptions:YDS']),('defensive_tds',['defensive:TD','interceptions:TD'])]
}
CATEGORIES={'passing':'passing_yards','rushing':'rushing_yards','receiving':'receiving_yards','tackles':'combined_tackles','sacks':'sacks','interceptions':'def_interceptions'}
BREAKERS={'passing':['passing_tds','passer_rating','completion_pct'],'rushing':['rushing_tds','yards_per_carry','carries'],'receiving':['receiving_tds','receptions','yards_per_reception'],'tackles':['tfl','sacks','passes_defended','def_interceptions'],'sacks':['tfl','qb_hits','combined_tackles'],'interceptions':['passes_defended','defensive_tds','interception_yards','combined_tackles']}
def player_leaders(rows,fbs):
 players={}
 for r in rows:
  team=canon(r.get('team'));pid=str(r.get('playerId') or '')
  if team not in fbs or not pid:continue
  p=players.setdefault((team,pid),{'id':pid,'name':r.get('player'),'stats':{},'raw':{}})
  key=str(r.get('category','')).lower()+':'+str(r.get('statType','')).upper()
  if key in p['raw'] and p['raw'][key]!=r.get('stat'):raise ValueError(f'Duplicate player stat {team} {pid} {key}')
  p['raw'][key]=r.get('stat')
 for p in players.values():
  for fields in FIELDS.values():
   for key,aliases in fields:
    value=next((num(p['raw'][a]) for a in aliases if num(p['raw'].get(a)) is not None),None)
    if value is not None:p['stats'][key]=value
  t=p['stats'];combined=str(p['raw'].get('passing:C/ATT',''))
  if 'combined_tackles' in t and 'solo_tackles' in t and 'assists' not in t and t['combined_tackles']>=t['solo_tackles']:t['assists']=t['combined_tackles']-t['solo_tackles']
  if '/' in combined:
   cmp,att=combined.split('/',1)
   if num(cmp) is not None and num(att) is not None:t.update(completions=num(cmp),attempts=num(att))
  if t.get('attempts',0)>0 and 'completions' in t:
   n=t['attempts'];t['completion_pct']=100*t['completions']/n
   if all(k in t for k in ['passing_yards','passing_tds','interceptions']):t['passer_rating']=(8.4*t['passing_yards']+330*t['passing_tds']+100*t['completions']-200*t['interceptions'])/n
  for rate,yards,attempts in [('yards_per_carry','rushing_yards','carries'),('yards_per_reception','receiving_yards','receptions')]:
   if t.get(attempts,0)>0 and yards in t:t[rate]=t[yards]/t[attempts]
  p.pop('raw')
 result={team:{} for team in fbs}
 for category,key in CATEGORIES.items():
  league=defaultdict(float)
  for (team,pid),p in players.items():league[pid]+=p['stats'].get(key,0)
  for team in fbs:
   eligible=[p for (t,pid),p in players.items() if t==team and p['stats'].get(key,0)>0]
   if not eligible:result[team][category]=None;continue
   keys=[key]+BREAKERS[category]
   p=sorted(eligible,key=lambda p:(tuple(-p['stats'].get(k,0) for k in keys),p['name'] or '',p['id']))[0]
   total=league[p['id']];result[team][category]=dict(p,rank=1+sum(v>total for v in league.values()),league_total=total,rank_field_size=sum(v>0 for v in league.values()))
 return result

def metric_pairs(advanced,stats):
 off=advanced.get('offense') or {};defense=advanced.get('defense') or {};pairs=[]
 mappings=[('PPA per play','ppa',False),('Success rate','successRate',True),('Explosiveness','explosiveness',False),('Points per scoring opportunity','pointsPerOpportunity',False),('Power success rate','powerSuccess',True),('Stuff rate','stuffRate',True),('Line yards per rush','lineYards',False),('Second-level yards','secondLevelYards',False),('Open-field yards','openFieldYards',False)]
 for label,path,pct in mappings:
  pairs.append({'label':label,'offense':num(off.get(path)),'defense':num(defense.get(path)),'percent':pct})
 for group,label in [('passingPlays','Passing'),('rushingPlays','Rushing'),('standardDowns','Standard downs'),('passingDowns','Passing downs')]:
  for key,title,pct in [('successRate','success rate',True),('ppa','PPA',False),('explosiveness','explosiveness',False)]:
   pairs.append({'label':label+' '+title,'offense':num((off.get(group) or {}).get(key)),'defense':num((defense.get(group) or {}).get(key)),'percent':pct})
 pairs.append({'label':'Havoc rate','offense':num((off.get('havoc') or {}).get('total')),'defense':num((defense.get('havoc') or {}).get('total')),'percent':True})
 for key,other,label in [('totalYards','opponentTotalYards','Total yards'),('netPassingYards','opponentNetPassingYards','Passing yards'),('rushingYards','opponentRushingYards','Rushing yards'),('turnovers','turnoversOpponent','Turnovers / turnovers forced'),('thirdDownConversions','opponentThirdDownConversions','3rd-down conversions')]:
  pairs.append({'label':label,'offense':stats.get(key),'defense':stats.get(key+'Opponent',stats.get(other)),'percent':False})
 for prefix,label in [('thirdDown','3rd-down conversion rate')]:
  values=[]
  for side in ['', 'opponent']:
   made=stats.get(prefix+'ConversionsOpponent',stats.get(side+prefix[0].upper()+prefix[1:]+'Conversions')) if side else stats.get(prefix+'Conversions')
   attempts=stats.get(prefix+'AttemptsOpponent',stats.get(side+prefix[0].upper()+prefix[1:]+'Attempts')) if side else stats.get(prefix+'Attempts')
   values.append(made/attempts if made is not None and attempts and attempts>0 else None)
  pairs.append({'label':label,'offense':values[0],'defense':values[1],'percent':True})
 return [p for p in pairs if p['offense'] is not None or p['defense'] is not None]

def collect(year,force=False):
 out=ROOT/'data/cfb/details'/f'{year}.json'
 if out.exists() and year<datetime.now(timezone.utc).year and not force:
  cached=json.loads(out.read_text())
  if not cached.get('basic_stats_collected'):
   rows,url=api('/stats/season',year=year);basic=defaultdict(dict)
   for r in rows:
    value=num(r.get('statValue'))
    if value is not None:basic[canon(r['team'])][r['statName']]=value
   oldlabels={'Total yards','Total yards per game','Passing yards','Passing yards per game','Rushing yards','Rushing yards per game','Turnovers / turnovers forced','3rd-down conversions','3rd-down conversion rate'}
   for team,d in cached['teams'].items():
    d['metrics']=[p for p in d['metrics'] if p['label'] not in oldlabels]+metric_pairs({},basic.get(team,{}))
   cached['basic_stats_collected']=True;cached['team_stat_catalog']=sorted({r['statName'] for r in rows})
   cached['updated_at']=datetime.now(timezone.utc).isoformat();out.write_text(json.dumps(cached,separators=(',',':')))
  if cached.get('leader_schema_version')!=2:
   rows,url=api('/stats/player/season',year=year,seasonType='both')
   leaders=player_leaders(rows,set(cached['teams']))
   for team,d in cached['teams'].items():d['leaders']=leaders[team]
   cached['leader_schema_version']=2;cached['updated_at']=datetime.now(timezone.utc).isoformat()
   out.write_text(json.dumps(cached,separators=(',',':')))
  return
 jobs=[('games','/games',{'year':year,'seasonType':'both'}),('lines','/lines',{'year':year,'seasonType':'both'}),('players','/stats/player/season',{'year':year,'seasonType':'both'}),('advanced','/stats/season/advanced',{'year':year,'excludeGarbageTime':'true'}),('stats','/stats/season',{'year':year}),('coaches','/coaches',{'year':year}),('recruiting','/recruiting/teams',{'year':year})]
 fetched={};sources=[]
 # Sequential calls per year keep concurrency bounded across the two year workers.
 for name,path,params in jobs:
  rows,url=api(path,**params);fetched[name]=rows;sources.append({'name':name,'url':url})
 old=json.loads((ROOT/'data/historical'/f'{year}.json').read_text())['games'];fbs={canon(g[side]) for g in old for side in ['home','away'] if (g.get(side+'_profile') or {}).get('classification')=='FBS'}
 for g in fetched['games']:
  for side in ['home','away']:
   if str(g.get(side+'Division','')).lower()=='fbs':fbs.add(canon(g[side+'Team']))
 leaders=player_leaders(fetched['players'],fbs)
 advanced={canon(r['team']):r for r in fetched['advanced']};basic=defaultdict(dict)
 for r in fetched['stats']:
  value=num(r.get('statValue'))
  if value is not None:basic[canon(r['team'])][r['statName']]=value
 coaches=defaultdict(list)
 for coach in fetched['coaches']:
  name=(coach.get('firstName','')+' '+coach.get('lastName','')).strip()
  for s in coach.get('seasons') or []:
   if str(s.get('year'))==str(year):coaches[canon(s['school'])].append({'name':name,'games':s.get('games'),'wins':s.get('wins'),'losses':s.get('losses'),'ties':s.get('ties'),'final_ap_rank':s.get('postseasonRank')})
 recruiting={canon(r['team']):{'rank':r.get('rank'),'points':r.get('points')} for r in fetched['recruiting']}
 def choose_line(rows):
  return next((r for r in rows if str(r.get('provider','')).lower()=='consensus'),next((r for r in rows if r.get('spread') is not None or r.get('overUnder') is not None),{}))
 lines={str(r['id']):choose_line(r.get('lines') or []) for r in fetched['lines']}
 games=[]
 for g in fetched['games']:
  if canon(g.get('homeTeam')) not in fbs and canon(g.get('awayTeam')) not in fbs:continue
  line=lines.get(str(g['id']),{})
  games.append({'game_id':str(g['id']),'season':year,'week':g.get('week'),'start_date':g.get('startDate'),'season_type':g.get('seasonType') or 'regular','notes':g.get('notes') or '',
   'home':g.get('homeTeam'),'away':g.get('awayTeam'),'home_id':g.get('homeId'),'away_id':g.get('awayId'),
   'home_conference':g.get('homeConference'),'away_conference':g.get('awayConference'),'neutral_site':g.get('neutralSite'),'conference_game':g.get('conferenceGame'),
   'home_profile':{'classification':'FBS' if canon(g.get('homeTeam')) in fbs else 'FCS/Other'},'away_profile':{'classification':'FBS' if canon(g.get('awayTeam')) in fbs else 'FCS/Other'},
   'spread':line.get('spread'),'over_under':line.get('overUnder'),'provider':line.get('provider'),
   'result':{'home_points':g['homePoints'],'away_points':g['awayPoints']} if g.get('completed') and g.get('homePoints') is not None and g.get('awayPoints') is not None else None})
 details={team:{'coaches':coaches.get(team,[]),'recruiting':recruiting.get(team),'metrics':metric_pairs(advanced.get(team,{}),basic.get(team,{})),'leaders':leaders.get(team,{})} for team in fbs}
 played=defaultdict(int)
 for g in games:
  if g['result']:
   played[canon(g['home'])]+=1;played[canon(g['away'])]+=1
 for team,d in details.items():
  for pair in d['metrics']:
   if pair['label'] in ['Total yards','Passing yards','Rushing yards'] and played[team]>0:
    pair['label']+=' per game'
    for side in ['offense','defense']:
     if pair[side] is not None:pair[side]/=played[team]
 assert len(details)>=120,f'{year}: incomplete FBS detail pool'
 assert sum(bool(d['leaders'].get('passing')) for d in details.values())>=100,f'{year}: missing passing leaders'
 out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps({'year':year,'updated_at':datetime.now(timezone.utc).isoformat(),'sources':sources,'games':games,'teams':details,'basic_stats_collected':True,'leader_schema_version':2,'player_stat_catalog':sorted({str(r.get('category'))+':'+str(r.get('statType')) for r in fetched['players']}),'team_stat_catalog':sorted({str(r.get('statName')) for r in fetched['stats']})},separators=(',',':')))
 print(f'{year}: {len(details)} FBS detail records; {len(games)} games; player categories '+str(sorted({r.get('category') for r in fetched['players']})),flush=True)

def main():
 years=range(2015,datetime.now(timezone.utc).year+1)
 with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(collect,years))
if __name__=='__main__':main()
