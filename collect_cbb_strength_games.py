#!/usr/bin/env python3
"""Daily ESPN final-box ledger for CBB strength, separate from dashboard phases.
Rechecks the last seven Eastern game dates; retries every unresolved final box.
"""
import argparse,json,time,urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,date,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from build_cbb_strength import possessions,save
ROOT=Path(__file__).resolve().parent
API='https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/'
def get(endpoint):
    for attempt in range(3):
        try:
            req=urllib.request.Request(API+endpoint,headers={'User-Agent':'BetWiseCBBStrength/1.0'})
            with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
        except Exception:
            if attempt==2:raise
            time.sleep(attempt+1)
def number(v):
    try:return float(v)
    except (ValueError,TypeError):return None
def pair(v):
    try:return tuple(float(x) for x in str(v).split('-'))
    except (ValueError,TypeError):return (None,None)
def box(row,score):
    stats={s['name']:s.get('displayValue') for s in row.get('statistics',[])}
    fg=pair(stats.get('fieldGoalsMade-fieldGoalsAttempted'));th=pair(stats.get('threePointFieldGoalsMade-threePointFieldGoalsAttempted'));ft=pair(stats.get('freeThrowsMade-freeThrowsAttempted'))
    return {'points':number(score),'fgm':fg[0],'fga':fg[1],'tpm':th[0],'ftm':ft[0],'fta':ft[1],'oreb':number(stats.get('offensiveRebounds')),'tov':number(stats.get('totalTurnovers',stats.get('turnovers')))}
def extract(event,known,season):
    c=event['competitions'][0];competitors=c['competitors'];ids=[str(v['team']['id']) for v in competitors]
    scores={str(v['team']['id']):number(v.get('score')) for v in competitors}
    if len(ids)!=2 or None in scores.values() or len(set(scores.values()))!=2:raise ValueError('Invalid final score')
    d1=[i for i in ids if i in known]
    if not d1:raise ValueError('No registered D1 team')
    result={'id':str(event['id']),'date':event['date'],'season':season,'phase':event['season']['type'],'home':next(str(v['team']['id']) for v in competitors if v['homeAway']=='home'),'neutral':bool(c.get('neutralSite')),'source':API+'summary?event='+str(event['id']),'verified_at':datetime.now(timezone.utc).isoformat()}
    if len(d1)==1:
        other=next(i for i in ids if i not in known);team=get('teams/'+other)['team'];group=team.get('groups') or {};parent=group.get('parent') or {}
        if not group.get('id') or not parent.get('id') or '50' in (str(group['id']),str(parent['id'])):raise ValueError('Unresolved or unregistered D1 opponent')
        result.update({'opponent_classification':'verified_non_d1','classification_source':API+'teams/'+other,'opponent_group':group,'teams':{i:{'points':scores[i]} for i in ids}})
        return result
    summary=get('summary?event='+str(event['id']));header=(summary.get('header') or {})
    hc=(header.get('competitions') or [{}])[0]
    if not (hc.get('status') or {}).get('type',{}).get('completed'):raise ValueError('Summary is not final')
    if str(header.get('season',{}).get('year',season))!=str(season):raise ValueError('Summary season mismatch')
    summary_scores={str(v['team']['id']):number(v.get('score')) for v in hc.get('competitors',[])}
    if summary_scores!=scores:raise ValueError('Final scores disagree')
    boxes={str(r['team']['id']):box(r,scores[str(r['team']['id'])]) for r in summary.get('boxscore',{}).get('teams',[]) if str(r['team']['id']) in ids}
    if set(boxes)!=set(ids):raise ValueError('Missing team box')
    possessions(list(boxes.values()));result['teams']=boxes;result['opponent_classification']='d1';return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--season',type=int,default=2027);args=p.parse_args();season=args.season
    today=datetime.now(ZoneInfo('America/New_York')).date();start=date(season-1,11,1);end=min(today-timedelta(days=1),date(season,6,30))
    # Never mutate a completed historical season through the daily updater.
    if today>date(season,7,1):raise RuntimeError('Season frozen; manual correction required')
    known={str(t['espn_id']) for t in json.loads((ROOT/'data/sports/team-registry.json').read_text())['teams'] if t['sport']=='cbb'}
    path=ROOT/f'data/cbb/strength-games/{season}.json'
    old=json.loads(path.read_text()) if path.exists() else {'season':season,'games':[],'pending_games':[]}
    if old['season']!=season:raise ValueError('Wrong ledger season')
    games={g['id']:g for g in old['games']};pending={g['event']['id']:g['event'] for g in old.get('pending_games',[])}
    last=date.fromisoformat(old['last_scanned']) if old.get('last_scanned') else start
    scan=max(start,last-timedelta(days=6));dates=[]
    while scan<=end:dates.append(scan);scan+=timedelta(days=1)
    boards=list(ThreadPoolExecutor(6).map(lambda d:get('scoreboard?groups=50&limit=1000&dates='+d.strftime('%Y%m%d')),dates))
    for board in boards:
        for e in board.get('events',[]):
            if e.get('season',{}).get('year')!=season or e['season'].get('type') not in (2,3):continue
            c=e['competitions'][0]
            if c.get('type',{}).get('abbreviation') not in (None,'STD'):continue
            if not any(str(v['team']['id']) in known for v in c['competitors']):continue
            if e.get('status',{}).get('type',{}).get('completed'):pending[e['id']]=e
    failures=[]
    def recover(e):
        try:return extract(e,known,season),None
        except Exception as exc:return None,{'event':e,'error':str(exc)}
    for game,error in ThreadPoolExecutor(6).map(recover,pending.values()):
        if game:games[game['id']]=game
        else:failures.append(error)
    save(path,{'season':season,'last_scanned':end.isoformat() if end>=start else None,'collected_at':datetime.now(timezone.utc).isoformat(),'games':sorted(games.values(),key=lambda g:(g['date'],g['id'])),'pending_games':failures})
    print(json.dumps({'season':season,'games':len(games),'pending':len(failures),'scoreboard_dates_checked':len(dates)}))
if __name__=='__main__':main()
