#!/usr/bin/env python3
"""Enrich active-season CBB team archives from verified ESPN completed-game boxes.

Uses the same completed-game source as the dashboard; never alters past seasons.
Do not fabricate player statistics for games without final boxes.
"""
import json
from collections import defaultdict
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent

def ratio(a,b,scale=1):
    return (a/b*scale) if b else None

def enrich(archives, boxes, year):
    indexed=defaultdict(list)
    for game in boxes:
        if int(game.get('season',0))!=year or int(game.get('phase',0)) not in (2,3):
            continue
        for team in game.get('teams',{}):
            indexed[str(team)].append(game)
    changed=0
    for path in sorted(archives.glob('*.json')):
        team=json.loads(path.read_text())
        tid=str(team['team_id'])
        season=team.get('seasons',{}).get(str(year))
        if not season or not indexed.get(tid):
            continue
        player_totals={}
        for phase,label in ((2,'regular'),(3,'postseason')):
            record=season.get('phases',{}).get(label)
            if not record:continue
            final={str(g['id']):g for g in record.get('games',[]) if g.get('status')=='final'}
            eligible=[g for g in indexed[tid] if int(g['phase'])==phase and str(g['id']) in final]
            # Do not publish partial season aggregates as though they cover all played games.
            if len(eligible)!=len(final) or not final:
                continue
            sums=defaultdict(float);opp=defaultdict(float)
            for g in eligible:
                own=g['teams'].get(tid)
                other=next((v for k,v in g['teams'].items() if str(k)!=tid),None)
                if not own or not other:break
                for key,value in own.items():
                    if isinstance(value,(int,float)):sums[key]+=value
                for key,value in other.items():
                    if isinstance(value,(int,float)):opp[key]+=value
                for p in g.get('players',{}).get(tid,[]):
                    ident=str(p['id']);row=player_totals.setdefault(ident,dict(id=ident,name=p['name'],position=p.get('position'),totals=defaultdict(float),games=0))
                    row['games']+=1
                    for key in ('minutes','points','rebounds','assists','steals','blocks','turnovers','fgm','fga','tpm','tpa','ftm','fta'):
                        if isinstance(p.get(key),(int,float)):row['totals'][key]+=p[key]
            else:
                n=len(eligible)
                def percent(m,a):return ratio(sums[m],sums[a],100)
                metrics=dict(
                    gamesPlayed=n,points=sums['points'],avgPoints=sums['points']/n,
                    rebounds=sums['reb'],totalRebounds=sums['reb'],avgRebounds=sums['reb']/n,
                    reboundsDifferential=sums['reb']-opp['reb'],
                    assists=sums['ast'],avgAssists=sums['ast']/n,
                    turnovers=sums['tov'],avgTurnovers=sums['tov']/n,opponentTurnovers=opp['tov'],
                    steals=sums['stl'],avgSteals=sums['stl']/n,blocks=sums['blk'],avgBlocks=sums['blk']/n,
                    fieldGoalsMade=sums['fgm'],fieldGoalsAttempted=sums['fga'],
                    threePointFieldGoalsMade=sums['tpm'],threePointFieldGoalsAttempted=sums['tpa'],
                    freeThrowsMade=sums['ftm'],freeThrowsAttempted=sums['fta'],
                    offensiveRebounds=sums['oreb'],fieldGoalPct=percent('fgm','fga'),
                    threePointFieldGoalPct=percent('tpm','tpa'),freeThrowPct=percent('ftm','fta'),
                    pointsInPaint=sums['paint_points'],avgPointsInPaint=sums['paint_points']/n,
                    opponentPointsInPaint=opp['paint_points'],
                    opponentFieldGoalsAttempted=opp['fga'],
                    opponentThreePointFieldGoalsAttempted=opp['tpa'])
                metrics['twoPointFieldGoalPct']=ratio(sums['fgm']-sums['tpm'],sums['fga']-sums['tpa'],100)
                if int(metrics['points'])!=sum(g['points'] for g in final.values()):
                    raise ValueError('Box totals mismatch '+path.name)
                record['metrics']=metrics
                record['coverage']='verified_box_scores'
        players=[]
        for row in player_totals.values():
            g=row['games'];t=row['totals']
            stats={'gamesPlayed':g,'avgMinutes':t['minutes']/g,'avgPoints':t['points']/g,
                   'avgRebounds':t['rebounds']/g,'avgAssists':t['assists']/g,
                   'avgSteals':t['steals']/g,'avgBlocks':t['blocks']/g,
                   'fieldGoalsAttempted':t['fga'],'threePointFieldGoalsAttempted':t['tpa'],'freeThrowsAttempted':t['fta'],
                   'fieldGoalPct':ratio(t['fgm'],t['fga'],100),
                   'threePointFieldGoalPct':ratio(t['tpm'],t['tpa'],100),
                   'freeThrowPct':ratio(t['ftm'],t['fta'],100),
                   'points':t['points'],'rebounds':t['rebounds'],'assists':t['assists'],
                   'steals':t['steals'],'blocks':t['blocks'],'turnovers':t['turnovers']}
            players.append(dict(id=row['id'],name=row['name'],position=row['position'],stats=stats))
        if players:
            players.sort(key=lambda p:-p['stats']['avgPoints'])
            season['players']=players
        path.write_text(json.dumps(team,separators=(',',':'),ensure_ascii=False)+'\n')
        changed+=1
    return changed

def main():
    year=datetime.now(timezone.utc).year+(datetime.now(timezone.utc).month>=7)
    source=ROOT/'cbb/dashboard/data/completed-games.json'
    boxes=json.loads(source.read_text()).get('games',[])
    count=enrich(ROOT/'data/cbb/teams',boxes,year)
    print('Enriched current-season CBB team archives:',count,'source final games:',len(boxes))
if __name__=='__main__':main()
