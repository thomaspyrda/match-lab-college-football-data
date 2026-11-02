#!/usr/bin/env python3
"""Publish the latest CBB season leaders from verified current-season team player archives."""
import json
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/cbb/division-one-season-leaders.json'
CATEGORIES={
 'points':('Points','points'),'avgPoints':('Points per Game','avgPoints'),
 'rebounds':('Rebounds','rebounds'),'avgRebounds':('Rebounds per Game','avgRebounds'),
 'assists':('Assists','assists'),'avgAssists':('Assists per Game','avgAssists'),
 'steals':('Steals','steals'),'avgSteals':('Steals per Game','avgSteals'),
 'blocks':('Blocks','blocks'),'avgBlocks':('Blocks per Game','avgBlocks'),
 'fieldGoalPct':('Field Goal %','fieldGoalPct'),
 'threePointFieldGoalPct':('3-Point %','threePointFieldGoalPct'),
 'freeThrowPct':('Free Throw %','freeThrowPct'),
 'avgMinutes':('Minutes per Game','avgMinutes')}
def publish():
 season=datetime.now(timezone.utc).year+(datetime.now(timezone.utc).month>=7)
 raw=json.loads(DATA.read_text())
 result={k:{'label':label,'leaders':[]} for k,(label,field) in CATEGORIES.items()}
 thresholds={'fieldGoalPct':('fieldGoalsAttempted',50),'threePointFieldGoalPct':('threePointFieldGoalsAttempted',25),'freeThrowPct':('freeThrowsAttempted',50)}
 players=[]
 for path in sorted((ROOT/'data/cbb/teams').glob('*.json')):
  team=json.loads(path.read_text())
  for player in team.get('seasons',{}).get(str(season),{}).get('players',[]):
   stats=player.get('stats') or {}
   gp=stats.get('gamesPlayed') or 0
   if gp<=0:continue
   players.append((player,stats,gp,path.stem))
 for key,(label,field) in CATEGORIES.items():
  qualifying=[p for p in players if key not in thresholds or (p[1].get(thresholds[key][0]) or 0)>=thresholds[key][1]]
  # For the active season, only waive the minimum until ten players qualify.
  eligible=[]
  for player,stats,gp,slug in (qualifying if key not in thresholds or len(qualifying)>=10 else players):
   val=stats.get(field)
   if not isinstance(val,(int,float)):continue
   entry={'name':player['name'],'team':slug,'id':str(player['id']),'gp':gp,'value':val}
   eligible.append(entry)
  eligible.sort(key=lambda x:(-x['value'],-x['gp'],x['name']))
  result[key]['leaders']=eligible[:10]
 raw.setdefault('seasons',{})[str(season)]=result
 DATA.write_text(json.dumps(raw,separators=(',',':'),ensure_ascii=False)+'\n')
 print('Published',season,'CBB season leaders from',len(players),'verified player archives')
if __name__=='__main__':publish()
