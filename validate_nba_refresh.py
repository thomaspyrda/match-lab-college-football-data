"""Reject a successful-looking NBA publish built from stale/inconsistent inputs."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent


def validate(cache, rankings, current, schedule, now=None):
    now=now or datetime.now(ZoneInfo('America/New_York'))
    today=now.astimezone(ZoneInfo('America/New_York')).date()
    year=today.year+(today.month>=7)
    freshness=cache.get('freshness') or {}
    if freshness.get('checked_through')!=str(today-timedelta(days=1)):
        raise ValueError('NBA results have not been checked through yesterday')
    games={str(g['id']):g for g in cache.get('games',[]) if g['season']==year and g['phase']==2}
    if set(freshness.get('expected_previous_day_games',[]))-games.keys():
        raise ValueError('Missing completed games from the previous day')
    season=rankings['seasons'][str(year)]
    if season['completed_games']!=len(games) or current['completed_games']!=len(games):
        raise ValueError('Rankings and team pages are not using the refreshed game cache')
    if len(season['teams'])!=30 or len(current['teams'])!=30 or len(schedule['teams'])!=30:
        raise ValueError('Expected all 30 teams in every current NBA output')
    if schedule.get('season')!=year:
        raise ValueError('Wrong full-schedule season')
    for team in schedule['teams'].values():
        if len(team['games'])!=82 or len({g['game_id'] for g in team['games']})!=82:
            raise ValueError('Expected 82 distinct schedule games/explicit NBA Cup slots')
    counts={tid:sum(tid in g['teams'] for g in games.values()) for g in games.values() for tid in g['teams']}
    if sum(r['games_played'] for r in season['teams'])!=2*len(games):
        raise ValueError('Rankings game totals do not reconcile')
    if any(r['games_played'] and r['metrics'].get('opp_points_in_paint') is None for r in season['teams']):
        raise ValueError('Points-in-the-paint coverage is incomplete')
    return {'season':year,'completed_games':len(games),'checked_through':freshness['checked_through'],'teams':30}


if __name__=='__main__':
    read=lambda p:json.loads((ROOT/p).read_text())
    print(validate(read('nba/dashboard/data/completed-games.json'),read('nba/rankings/data/nba-team-rankings.json'),read('nba/teams/data/current-season.json'),read('nba/teams/data/current-schedule.json')))
