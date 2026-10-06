#!/usr/bin/env python3
"""NBA dashboard: completed ESPN box scores, isolated season types, observed snapshots."""
from __future__ import annotations
import json, time, urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
API='https://site.api.espn.com/apis/site/v2/sports/basketball/nba/'
UTC=timezone.utc

def get(endpoint):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(API+endpoint,timeout=25) as r:return json.load(r)
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)

def stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
def num(value):
    try:return float(str(value).replace('+',''))
    except (ValueError,TypeError):return None
def minutes(value):
    if ':' in str(value):
        a,b=str(value).split(':');return float(a)+float(b)/60
    return num(value)
def pair(value):
    try:return [float(x) for x in str(value).split('-')]
    except ValueError:return [None,None]

def team_box(row,score):
    values={s['name']:s.get('displayValue') for s in row['statistics']}
    fg=pair(values.get('fieldGoalsMade-fieldGoalsAttempted'))
    th=pair(values.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted'))
    ft=pair(values.get('freeThrowsMade-freeThrowsAttempted'))
    return {'points':num(score),'fgm':fg[0],'fga':fg[1],'tpm':th[0],'tpa':th[1],'ftm':ft[0],'fta':ft[1],
      'oreb':num(values.get('offensiveRebounds')),'dreb':num(values.get('defensiveRebounds')),'reb':num(values.get('totalRebounds')),
      'ast':num(values.get('assists')),'tov':num(values.get('totalTurnovers',values.get('turnovers'))),'stl':num(values.get('steals')),'blk':num(values.get('blocks'))}

def players_box(row):
    result=[]
    for group in row.get('statistics',[]):
        keys=group.get('keys',[])
        for entry in group.get('athletes',[]):
            values=dict(zip(keys,entry.get('stats',[])))
            played=minutes(values.get('minutes'))
            if entry.get('didNotPlay') or played is None or played<=0:continue
            athlete=entry['athlete'];fg=pair(values.get('fieldGoalsMade-fieldGoalsAttempted'));th=pair(values.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted'));ft=pair(values.get('freeThrowsMade-freeThrowsAttempted'))
            result.append({'id':'nba:espn:player:'+athlete['id'],'name':athlete['displayName'],'position':athlete.get('position',{}).get('abbreviation','—'),
              'headshot':athlete.get('headshot',{}).get('href'),'minutes':played,'points':num(values.get('points')),'rebounds':num(values.get('rebounds')),
              'assists':num(values.get('assists')),'turnovers':num(values.get('turnovers')),'plus_minus':num(values.get('plusMinus')),
              'fgm':fg[0],'fga':fg[1],'tpm':th[0],'tpa':th[1],'ftm':ft[0],'fta':ft[1]})
    return result

def completed(event):
    summary=get('summary?event='+event['id']); comp=event['competitions'][0]
    scores={c['team']['id']:c.get('score') for c in comp['competitors']}
    boxes={r['team']['id']:team_box(r,scores[r['team']['id']]) for r in summary.get('boxscore',{}).get('teams',[]) if r['team']['id'] in scores}
    if len(boxes)!=2:raise ValueError('Incomplete team box score '+event['id'])
    players={r['team']['id']:players_box(r) for r in summary.get('boxscore',{}).get('players',[])}
    return {'id':event['id'],'date':event['date'],'season':event['season']['year'],'phase':event['season']['type'],
      'observed_complete_at':datetime.now(UTC).isoformat(),'teams':boxes,'players':players,'home':next(c['team']['id'] for c in comp['competitors'] if c['homeAway']=='home'),
      'neutral':comp.get('neutralSite',False),'game_id':'nba:espn:game:'+event['id'],
      'source':'https://www.espn.com/nba/boxscore/_/gameId/'+event['id']}

def ratio(a,b,scale=1):return a/b*scale if b and a is not None else None

def profile(team_id,history,cutoff):
    games=sorted([g for g in history if team_id in g['teams'] and stamp(g['observed_complete_at'])<=cutoff],key=lambda g:g['date'])
    totals=defaultdict(float);other=defaultdict(float);player_totals={};possessions=0;poss_games=0;wins=losses=0;results=[]
    for game in games:
        own=game['teams'][team_id];oid=next(i for i in game['teams'] if i!=team_id);opp=game['teams'][oid]
        for k,v in own.items():
            if v is not None:totals[k]+=v
        for k,v in opp.items():
            if v is not None:other[k]+=v
        required=['fga','oreb','tov','fta']
        if all(own.get(k) is not None and opp.get(k) is not None for k in required):
            possessions+=(own['fga']-own['oreb']+own['tov']+.44*own['fta']+opp['fga']-opp['oreb']+opp['tov']+.44*opp['fta'])/2;poss_games+=1
        won=own['points']>opp['points'];wins+=won;losses+=not won
        results.append({'date':game['date'],'opponent_id':oid,'location':'Neutral' if game.get('neutral') else ('Home' if game['home']==team_id else 'Away'),'result':'W' if won else 'L','score':f"{int(own['points'])}–{int(opp['points'])}"})
        for p in game.get('players',{}).get(team_id,[]):
            target=player_totals.setdefault(p['id'],{'id':p['id'],'name':p['name'],'position':p['position'],'headshot':p['headshot'],'games':0,'totals':defaultdict(float),'pm_games':0})
            target['games']+=1
            for k in ['minutes','points','rebounds','assists','turnovers','plus_minus','fgm','fga','tpm','tpa','ftm','fta']:
                if p.get(k) is not None:target['totals'][k]+=p[k]
            if p.get('plus_minus') is not None:target['pm_games']+=1
    n=len(games);valid_poss=n>0 and poss_games==n
    values={'ortg':ratio(totals.get('points'),possessions,100) if valid_poss else None,'drtg':ratio(other.get('points'),possessions,100) if valid_poss else None,
      'efg':ratio(totals.get('fgm',0)+.5*totals.get('tpm',0),totals.get('fga'),100) if n else None,
      'opp_efg':ratio(other.get('fgm',0)+.5*other.get('tpm',0),other.get('fga'),100) if n else None,
      'three_pct':ratio(totals.get('tpm'),totals.get('tpa'),100),'opp_three_pct':ratio(other.get('tpm'),other.get('tpa'),100),
      'orb_pct':ratio(totals.get('oreb'),totals.get('oreb',0)+other.get('dreb',0),100) if n else None,
      'opp_orb_pct':ratio(other.get('oreb'),other.get('oreb',0)+totals.get('dreb',0),100) if n else None,
      'tov_pct':ratio(totals.get('tov'),possessions,100) if valid_poss else None,'forced_tov_pct':ratio(other.get('tov'),possessions,100) if valid_poss else None,
      'ft_rate':ratio(totals.get('fta'),totals.get('fga'),100),'opp_ft_rate':ratio(other.get('fta'),other.get('fga'),100)}
    players=[]
    for p in player_totals.values():
        t=p.pop('totals');count=p['games'];p['per_game']={k:round(t[k]/count,1) for k in ['minutes','points','rebounds','assists','turnovers']};p['plus_minus']=round(t['plus_minus']/p['pm_games'],1) if p['pm_games'] else None
        p['fg_pct']=ratio(t['fgm'],t['fga'],100);p['three_pct']=ratio(t['tpm'],t['tpa'],100);p['bpm']=None;p['vorp']=None;p['vorp_percentile']=None;players.append(p)
    players.sort(key=lambda p:(p['per_game']['minutes'],p['per_game']['points']),reverse=True)
    return {'games':n,'record':f'{wins}–{losses}' if n else '—','ppg':round(totals['points']/n,1) if n else None,'allowed':round(other['points']/n,1) if n else None,
      'metrics':values,'players':players[:5],'results':results[-5:],'last_game_date':games[-1]['date'] if games else None}

def rank(profiles,key,high):
    values=sorted([(i,p['metrics'][key]) for i,p in profiles.items() if p['metrics'].get(key) is not None],key=lambda r:r[1],reverse=high)
    return {i:{'value':round(v,1),'rank':1+sum((x>v if high else x<v) for _,x in values),'population':len(values),'percentile':round(100*sum((x<v if high else x>v) for _,x in values)/max(len(values)-1,1))} for i,v in values}

METRICS=[('ortg','Offensive rating','OFFENSE',True,''),('drtg','Defensive rating','DEFENSE',False,''),('efg','Effective FG%','OFFENSE',True,'%'),('opp_efg','Effective FG% allowed','DEFENSE',False,'%'),('three_pct','Three-point FG%','OFFENSE',True,'%'),('opp_three_pct','Three-point FG% allowed','DEFENSE',False,'%'),('orb_pct','Offensive rebound rate','OFFENSE',True,'%'),('opp_orb_pct','Offensive rebound rate allowed','DEFENSE',False,'%'),('tov_pct','Turnover rate','OFFENSE',False,'%'),('forced_tov_pct','Turnovers forced rate','DEFENSE',True,'%'),('ft_rate','Free-throw attempt rate','OFFENSE',True,'%'),('opp_ft_rate','Free-throw attempt rate allowed','DEFENSE',False,'%')]

def season_history(games,season,phase):return [g for g in games if g['season']==season and g['phase']==phase]

def main():
    now=datetime.now(UTC);today=now.astimezone(ZoneInfo('America/New_York')).date();season=today.year+(today.month>=7)
    registry=json.loads((ROOT/'data/sports/team-registry.json').read_text());teams={t['espn_id']:t for t in registry['teams'] if t['sport']=='nba'}
    cache_path=ROOT/'nba/dashboard/data/completed-games.json';cache=json.loads(cache_path.read_text()) if cache_path.exists() else {'games':[]}
    old={g['id']:g for g in cache['games'] if g['season']==season}
    start=max(today-timedelta(days=7),today.replace(month=10,day=1)) if today.month>=10 else today-timedelta(days=7)
    if not old and today.month==10:start=today.replace(day=1)
    dates=[start+timedelta(days=i) for i in range((today+timedelta(days=7)-start).days+1)]
    boards=list(ThreadPoolExecutor(8).map(lambda d:get('scoreboard?dates='+d.strftime('%Y%m%d')),dates))
    events={e['id']:e for b in boards for e in b.get('events',[]) if e.get('season',{}).get('year')==season and all(c['team']['id'] in teams for c in e['competitions'][0]['competitors'])}
    new=[e for e in events.values() if e['status']['type'].get('completed') and e['id'] not in old]
    for g in ThreadPoolExecutor(8).map(completed,new):old[g['id']]=g
    for g in old.values():
        g['game_id']='nba:espn:game:'+g['id']
        if g['id'] in events:g['neutral']=events[g['id']]['competitions'][0].get('neutralSite',False)
    phases=[e['season']['type'] for e in events.values() if stamp(e['date']).astimezone(ZoneInfo('America/New_York')).date()<=today]
    latest_phase=max(phases) if phases else (min(events.values(),key=lambda e:e['date'])['season']['type'] if events else 2)
    history=season_history(old.values(),season,latest_phase)
    refreshed=datetime.now(UTC)
    slate=[e for e in events.values() if e['season']['type']==latest_phase and not e['status']['type'].get('completed') and stamp(e['date'])>=now-timedelta(hours=8)]
    if not slate:slate=sorted([e for e in events.values() if e['season']['type']==latest_phase],key=lambda e:e['date'],reverse=True)[:5]
    output=[]
    for event in sorted(slate,key=lambda e:e['date']):
        tip=stamp(event['date']);cutoff=min(tip,refreshed);profiles={i:profile(i,history,cutoff) for i in teams}
        comp=event['competitions'][0];sides={c['homeAway']:c for c in comp['competitors']};away=sides['away']['team']['id'];home=sides['home']['team']['id']
        def team(i):
            t=teams[i];return {'id':i,'team_id':t['id'],'name':t['name'],'abbr':t['abbreviation'],'logo':t['logo'],'color':'#'+sides['away' if i==away else 'home']['team'].get('color','666666'),'profile':profiles[i]}
        metrics=[]
        for key,label,unit,high,suffix in METRICS:
            ranks=rank(profiles,key,high);metrics.append({'key':key,'label':label,'unit':unit,'high':high,'suffix':suffix,'away':ranks.get(away),'home':ranks.get(home)})
        odds=comp.get('odds',[]);line=odds[0] if odds else {};provider=line.get('provider',{}).get('name')
        output.append({'id':event['id'],'date':event['date'],'label':tip.astimezone(ZoneInfo('America/New_York')).strftime('%a %b %-d · %-I:%M %p ET'),
          'status':event['status']['type']['description'],'away':team(away),'home':team(home),'metrics':metrics,
          'venue':comp.get('venue',{}).get('fullName','Venue unavailable'),'neutral':comp.get('neutralSite',False),
          'market':{'spread':line.get('details'),'total':line.get('overUnder'),'provider':provider,'observed_at':refreshed.isoformat() if line else None},
          'source':'https://www.espn.com/nba/game/_/gameId/'+event['id'],'profile_cutoff':cutoff.isoformat()})
    data={'schema_version':1,'season':f'{season-1}–{str(season)[2:]}','season_type':{1:'Preseason',2:'Regular season',3:'Playoffs'}[latest_phase],'updated_at':refreshed.isoformat(),
      'completed_games':len(history),'games':output,'coverage':{'bpm':'Unavailable from this feed','vorp':'Unavailable from this feed','injuries':'Not yet connected; verify current availability','refresh':'Hourly snapshot, not a live scoreboard'},
      'methodology':'Ratings use estimated possessions: average of both teams’ FGA − OREB + TO + 0.44 × FTA. Rankings include only teams with completed games in this season type. Completed results must have been observed before the selected tipoff; historical first-seen timestamps are not backdated.'}
    dest=ROOT/'nba/dashboard/data/dashboard.json';dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(json.dumps(data,indent=2)+'\n');cache_path.write_text(json.dumps({'schema_version':1,'games':list(old.values())},indent=2)+'\n')
    assert len(teams)==30 and output,'No NBA teams or slate loaded'
    print(f"NBA {data['season_type']}: {len(output)} matchups, {len(history)} completed games, {sum(len(g['players'].get(i,[])) for g in history for i in g['players'])} player game records")

if __name__=='__main__':main()
