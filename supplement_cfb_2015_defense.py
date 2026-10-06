"""Fill CFBD's 2015 defensive-stat gap with ESPN season-type totals."""
import json, re, time, urllib.request, urllib.error
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from refresh_cfb_team_details import BREAKERS,canon
ROOT=Path(__file__).resolve().parent
BASE='https://sports.core.api.espn.com/v2/sports/football/leagues/college-football/seasons/2015'
KEYS={'totalTackles':('tackles','combined_tackles'),'sacks':('sacks','sacks'),'interceptions':('interceptions','def_interceptions')}
STAT_KEYS={'totalTackles':'combined_tackles','soloTackles':'solo_tackles','assistTackles':'assists','sacks':'sacks','tacklesForLoss':'tfl','hurries':'qb_hits','passesDefended':'passes_defended','interceptions':'def_interceptions','interceptionYards':'interception_yards','interceptionTouchdowns':'interception_tds','defensiveFumblesTouchdowns':'fumble_tds'}
def ranked_copy(player,key,league):
 total=league[key][player['id']]
 return dict(player,rank=1+sum(v>total for v in league[key].values()),league_total=total,rank_field_size=sum(v>0 for v in league[key].values()))
def get(url,missing=False):
 url=url.replace('http:','https:')
 for attempt in range(3):
  try:
   with urllib.request.urlopen(url,timeout=35) as r:return json.load(r)
  except urllib.error.HTTPError as e:
   if missing and e.code==404:return None
   if attempt==2:raise
  except Exception:
   if attempt==2:raise
  time.sleep(1+attempt)

def main():
 path=ROOT/'data/cfb/details/2015.json'
 data=json.loads(path.read_text())
 if data.get('defense_supplement_version')==2:return
 ids={}
 for g in data['games']:
  for side in ['home','away']:
   name=canon(g[side])
   if name in data['teams']:ids[name]=str(g[side+'_id'])
 post={canon(g[side]) for g in data['games'] if g['season_type']=='postseason' and g.get('result') for side in ['home','away']}
 def team_pool(item):
  team,tid=item;players={}
  for phase in [2]+([3] if team in post else []):
   d=get(f'{BASE}/types/{phase}/teams/{tid}/leaders?lang=en&region=us',missing=phase==3) or {}
   for category in d.get('categories',[]):
    if category['name'] not in KEYS:continue
    key=KEYS[category['name']][1]
    for row in category.get('leaders',[]):
     athlete_url=row['athlete']['$ref'];pid=re.search(r'/athletes/(\d+)',athlete_url)[1]
     p=players.setdefault(pid,{'id':pid,'totals':defaultdict(float),'athlete_url':athlete_url,'team_id':tid,'team':team})
     p['totals'][key]+=float(row['value'])
  if not players:raise ValueError(f'No 2015 defensive leader pool for {team}')
  return team,players
 with ThreadPoolExecutor(max_workers=8) as pool:team_players=dict(pool.map(team_pool,ids.items()))
 league={key:defaultdict(float) for category,key in KEYS.values()}
 candidates={}
 for team,players in team_players.items():
  for p in players.values():
   for key in league:league[key][p['id']]+=p['totals'].get(key,0)
  for category,key in KEYS.values():
   maximum=max((p['totals'].get(key,0) for p in players.values()),default=0)
   if maximum>0:
    for p in players.values():
     if p['totals'].get(key,0)==maximum:candidates[(team,p['id'])]=p
 def player_detail(item):
  (team,pid),p=item;stats=defaultdict(float);observed=set()
  for phase in [2]+([3] if team in post else []):
   url=f'{BASE}/types/{phase}/teams/{p["team_id"]}/athletes/{pid}/statistics/0?lang=en&region=us'
   d=get(url,missing=True) or {}
   for category in d.get('splits',{}).get('categories',[]):
    for row in category.get('stats',[]):
     key=STAT_KEYS.get(row['name'])
     if key and row.get('value') is not None:stats[key]+=float(row['value']);observed.add(key)
  for key in league:
   if key in observed and stats[key]!=p['totals'].get(key,0):raise ValueError(f'ESPN leader/stat mismatch {team} {pid} {key}')
  athlete=get(p['athlete_url']);stats=dict(stats)
  if 'interception_tds' in stats or 'fumble_tds' in stats:stats['defensive_tds']=stats.get('interception_tds',0)+stats.get('fumble_tds',0)
  return (team,pid),{'id':pid,'name':athlete['displayName'],'position':(athlete.get('position') or {}).get('abbreviation'),'stats':stats,'source':'ESPN','source_url':p['athlete_url'].replace('http:','https:')}
 with ThreadPoolExecutor(max_workers=8) as pool:full=dict(pool.map(player_detail,candidates.items()))
 for team,players in team_players.items():
  for category,key in KEYS.values():
   maximum=max((p['totals'].get(key,0) for p in players.values()),default=0)
   if maximum<=0:data['teams'][team]['leaders'][category]=None;continue
   eligible=[full[(team,p['id'])] for p in players.values() if p['totals'].get(key,0)==maximum]
   keys=[key]+BREAKERS[category]
   p=sorted(eligible,key=lambda p:(tuple(-p['stats'].get(k,0) for k in keys),p['name'],p['id']))[0]
   data['teams'][team]['leaders'][category]=ranked_copy(p,key,league)
 data['sources'].append({'name':'2015 defensive leaders and player season statistics (regular + postseason)','url':BASE})
 data['defense_supplement_version']=2;data['defense_supplement_teams']=len(team_players)
 data['updated_at']=datetime.now(timezone.utc).isoformat();path.write_text(json.dumps(data,separators=(',',':')))
 print(f'Filled 2015 defensive leaders from ESPN for {len(team_players)} FBS teams',flush=True)
if __name__=='__main__':main()
