"""Refresh first-round NFL picks for CFB programs using CFBD's historical draft API.

The NFL team pages provide the 2015-2026 archive. This script adds the earlier
NFL first rounds beginning in 1970, keeping only schools with current CFB pages.
"""
import json, os, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/cfb/program-accolades.json'
REGISTRY=ROOT/'data/cfb/team-registry.json'
API='https://api.collegefootballdata.com/draft/picks'
DOCS='https://api.collegefootballdata.com/api/draft'
START_YEAR=1970
END_YEAR=2014
NFL_SOURCE='https://nfl.parlaycalculator.bet/'

def fetch_year(year,key):
    url=API+'?'+urllib.parse.urlencode({'year':year})
    req=urllib.request.Request(url,headers={'Authorization':'Bearer '+key,'Accept':'application/json','User-Agent':'MatchLab-CFB-Program-Accolades'})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2:raise
            time.sleep(2*(attempt+1))
    raise RuntimeError(f'Unable to fetch draft picks for {year}')

def main():
    key=os.environ.get('CFBD_API_KEY')
    if not key:raise RuntimeError('CFBD_API_KEY is required to refresh historical draft picks')
    data=json.loads(DATA.read_text())
    registry=json.loads(REGISTRY.read_text())['teams']
    team_ids={str(t['id']) for t in registry}
    # Keep NFL-page selections already imported for 2015-2026.
    current=[]
    for tid,team in data['teams'].items():
        current.extend(dict(r,team_id=str(tid)) for r in team.get('first_round_draft_picks',[]) if 2015<=int(r['year'])<=2026)
        team['first_round_draft_picks']=[]
    current_years={int(r['year']) for r in current}
    if min(current_years,default=0)!=2015 or max(current_years,default=0)!=2026 or len(current)<300:
        raise ValueError('Existing NFL team-page archive must cover first-round picks from 2015 through 2026')
    rows=[];unmatched=0
    for year in range(START_YEAR,END_YEAR+1):
        payload=fetch_year(year,key)
        if not isinstance(payload,list):raise ValueError(f'Unexpected draft response for {year}')
        first=[p for p in payload if int(p.get('round') or 0)==1]
        if not 20<=len(first)<=36:raise ValueError(f'Unexpected first-round count for {year}: {len(first)}')
        for p in first:
            college_id=str(p.get('collegeId') or '')
            if college_id not in team_ids:
                unmatched+=1
                continue
            overall=int(p.get('overall') or p.get('pick') or 0)
            if not 1<=overall<=36:raise ValueError(f'Invalid overall pick in {year}: {overall}')
            rows.append({'team_id':college_id,'year':year,'player':p.get('name') or 'Unknown','position':p.get('position') or '',
                'overall_pick':overall,'nfl_team':p.get('nflTeam') or '—','source':'NFLDraft:CFBD'})
        time.sleep(0.15)
    if len(rows)<900:raise ValueError(f'Too few historical first-round picks mapped to current CFB teams: {len(rows)}')
    seen=set()
    for record in current+rows:
        keyrow=(str(record['team_id']),int(record['year']),int(record['overall_pick']),record['player'])
        if keyrow in seen:raise ValueError(f'Duplicate first-round pick: {keyrow}')
        seen.add(keyrow)
    for record in current+rows:
        tid=str(record.pop('team_id'))
        data['teams'][tid]['first_round_draft_picks'].append(record)
    for team in data['teams'].values():
        team['first_round_draft_picks'].sort(key=lambda r:(-int(r['year']),int(r['overall_pick']),r['player']))
    data['sources']['NFLDraft:CFBD']={'name':'CollegeFootballData historical NFL draft picks','url':DOCS}
    picks=[p for team in data['teams'].values() for p in team['first_round_draft_picks']]
    years=[int(p['year']) for p in picks]
    data['coverage']['nfl_first_round_draft_from']=min(years)
    data['coverage']['nfl_first_round_draft_through']=max(years)
    data['coverage']['nfl_first_round_draft_count']=len(picks)
    data['coverage']['nfl_first_round_draft_unmatched_pre_2015']=unmatched
    data['updated_at']=datetime.now(timezone.utc).isoformat()
    DATA.write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False))
    print(f'Refreshed {len(rows)} 1970-2014 first-round selections for current CFB pages; {len(current)} NFL-page selections retained; {unmatched} historical picks are outside the current FBS page registry.')

if __name__=='__main__':main()
