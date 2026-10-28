"""Merge the full published NBA schedule with verified completed results.

The NBA initially publishes 80 dated games. Two genuine NBA Cup schedule
slots are explicitly TBD until assigned; they are never invented opponents.
"""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from refresh_nba_dashboard import get, stamp

ROOT = Path(__file__).resolve().parent
CUP_SOURCE = 'https://pr.nba.com/2026-27-nba-regular-season-schedule'


def build_team(data, team_id, lookup, completed, year):
    if data.get('requestedSeason', {}).get('year') != year or data.get('requestedSeason', {}).get('type') != 2:
        raise ValueError('Wrong NBA schedule season or phase')
    games = {}
    for event in data.get('events', []):
        if event.get('seasonType', {}).get('type') != 2 or event.get('season', {}).get('year') != year:
            continue
        comp = event['competitions'][0]
        sides = {str(c['team']['id']): c for c in comp.get('competitors', [])}
        if team_id not in sides or len(sides) != 2:
            raise ValueError('Invalid schedule participants')
        other = next(i for i in sides if i != team_id)
        if other not in lookup:
            raise ValueError('Unknown NBA opponent')
        gid = str(event['id'])
        if gid in games:
            raise ValueError('Duplicate NBA schedule event')
        date = stamp(event['date']).astimezone(ZoneInfo('America/New_York')).date().isoformat()
        status = comp.get('status', {}).get('type', {})
        row = {'game_id':gid, 'date':date, 'tipoff':event['date'],
               'location':'Home' if sides[team_id]['homeAway']=='home' else 'Away',
               'neutral':bool(comp.get('neutralSite')), 'opponent_slug':lookup[other]['slug'],
               'opponent_name':lookup[other]['name'], 'status':status.get('description','Scheduled')}
        if gid in completed:
            row.update(completed[gid])
            row['date']=date
        elif status.get('completed'):
            # Results can be displayed from the official schedule even while
            # separately sourced closing lines/advanced boxes are unavailable.
            own = sides[team_id].get('score'); opp = sides[other].get('score')
            if isinstance(own, dict): own = own.get('value')
            if isinstance(opp, dict): opp = opp.get('value')
            if own is None or opp is None: raise ValueError('Final schedule event missing scores')
            own, opp = int(float(own)), int(float(opp))
            if own == opp: raise ValueError('Final NBA game cannot be tied')
            row.update(score_for=own,score_against=opp,result='W' if own>opp else 'L')
        games[gid] = row
    for gid, row in completed.items():
        if gid not in games: games[gid] = row
    rows = sorted(games.values(), key=lambda g:(g['date'],str(g['game_id'])))
    if not 80 <= len(rows) <= 82:
        raise ValueError(f'Incomplete full NBA schedule for {team_id}: {len(rows)} games')
    pending = 82-len(rows)
    for i in range(pending):
        rows.append({'game_id':f'nba-cup-tbd-{team_id}-{i+1}', 'date':None,
                     'location':'TBD','opponent_name':'NBA Cup scheduling — opponent/date TBD',
                     'status':'NBA Cup schedule slot pending','schedule_pending':True})
    for n,row in enumerate(rows,1):row['game_number']=n
    return {'games':rows,'dated_games':82-pending,'pending_cup_games':pending,'source':f'https://www.espn.com/nba/team/schedule/_/id/{team_id}/season/{year}'}


def main():
    now=datetime.now(ZoneInfo('America/New_York'));year=now.year+(now.month>=7)
    registry=json.loads((ROOT/'data/sports/team-registry.json').read_text())
    lookup={str(t['espn_id']):t for t in registry['teams'] if t['sport']=='nba'}
    if len(lookup)!=30:raise ValueError('Expected 30 NBA schedule teams')
    def one(tid):
        details=json.loads((ROOT/'nba/teams/data'/f'{lookup[tid]["slug"]}-season-details.json').read_text())
        completed={str(g['game_id']):g for g in details.get('seasons',{}).get(str(year),{}).get('games',[]) if g.get('result') in ('W','L')}
        data=get(f'teams/{tid}/schedule?season={year}&seasontype=2')
        return lookup[tid]['slug'],build_team(data,tid,lookup,completed,year)
    teams=dict(ThreadPoolExecutor(4).map(one,lookup))
    output={'season':year,'updated_at':now.isoformat(),'cup_source':CUP_SOURCE,'teams':teams}
    (ROOT/'nba/teams/data/current-schedule.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':'))+'\n')
    print('Published all 30 full schedules: 82 games/slots per team, including explicit unassigned NBA Cup slots.')


if __name__=='__main__':main()
