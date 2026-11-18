"""NBA.com/Synergy transition play types; separate from ESPN fastbreak points."""
import json, math, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta
ROOT=Path(__file__).resolve().parent
DEST=ROOT/'nba/dashboard/data/transition.json'
def refresh(season):
    result={'schema':1,'season':season,'checked_at':datetime.now(timezone.utc).isoformat(),'source':'https://www.nba.com/stats/teams/transition','status':'unavailable','teams':{}}
    try:
        for side in ('offensive','defensive'):
            url='https://stats.nba.com/stats/synergyplaytypes?LeagueID=00&SeasonYear='+str(season-1)+'-'+str(season)[2:]+'&SeasonType=Regular%20Season&PerMode=PerGame&PlayerOrTeam=T&TypeGrouping='+side+'&PlayType=Transition'
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://www.nba.com/'})
            with urllib.request.urlopen(req,timeout=25) as response: data=json.load(response)
            table=data['resultSets'][0]
            assert len(table['rowSet'])==30,'Incomplete transition coverage'
            for values in table['rowSet']:
                row=dict(zip(table['headers'],values))
                assert row['PLAY_TYPE']=='Transition' and row['SEASON_ID']=='2'+str(season-1)
                assert all(isinstance(row[k],(int,float)) and math.isfinite(row[k]) and row[k]>=0 for k in ('GP','PTS'))
                result['teams'].setdefault(row['TEAM_ABBREVIATION'],{})[side]={'games':row['GP'],'points':row['PTS']}
        assert len(result['teams'])==30
        result['status']='available'
    except Exception as exc:
        result['teams']={};result['reason']=str(exc)
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,separators=(',',':'))+'\n')
    print('NBA transition source:',json.dumps({k:v for k,v in result.items() if k!='teams'}),flush=True)
    return result
def metrics(abbr, games, season, cutoff=None):
    empty={'transition_points':None,'opp_transition_points':None}
    try:
        data=json.loads(DEST.read_text())
        checked=datetime.fromisoformat(data['checked_at'].replace('Z','+00:00'))
        now=datetime.now(timezone.utc)
        if data.get('status')!='available' or data['season']!=season or not timedelta(0)<=now-checked<=timedelta(hours=30):return empty
        if cutoff is not None and checked>cutoff:return empty
        abbr={'BRK':'BKN','CHO':'CHA','PHO':'PHX','GS':'GSW','NY':'NYK','SA':'SAS','NO':'NOP'}.get(abbr,abbr)
        row=data['teams'][abbr]
        return {key:row[side]['points'] if row[side]['games']==games and games else None for key,side in [('transition_points','offensive'),('opp_transition_points','defensive')]}
    except (OSError,ValueError,KeyError,TypeError):return empty
def profile_metrics(team_id, games, cutoff):
    if not games or any(g.get('phase')!=2 for g in games):return {'transition_points':None,'opp_transition_points':None}
    try:
        registry=json.loads((ROOT/'data/sports/team-registry.json').read_text())
        team=next(t for t in registry['teams'] if t['sport']=='nba' and str(t['espn_id'])==str(team_id))
        return metrics(team['abbreviation'],len(games),games[0]['season'],cutoff)
    except (OSError,ValueError,KeyError,StopIteration):
        return {'transition_points':None,'opp_transition_points':None}
