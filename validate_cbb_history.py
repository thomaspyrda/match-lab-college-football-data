"""Validate historical completeness, known finishes, coverage, and market grading."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main(require_2026=True):
    read=lambda name:json.loads((ROOT/'data/cbb'/name).read_text())
    conf,nat,awards=map(read,['conference-tournament-results.json','tournament-results.json','national-awards.json'])
    end=2027 if require_2026 else 2026
    for year in map(str,range(2016,end)):
        assert len(conf['seasons'][year])==365
        assert len(nat['seasons'][year])==365
        assert all(x.get('result') and 'not verified' not in x['result'] for x in conf['seasons'][year].values())
        assert all(x.get('tournament')!='unverified' for x in nat['seasons'][year].values())
        if year!='2020':assert sum(x.get('tournament')=='NCAA' for x in nat['seasons'][year].values()) in (67,68)
    assert 'Champion' in conf['seasons']['2025']['duke-blue-devils']['result']
    assert '73–62' in conf['seasons']['2025']['duke-blue-devils']['result']
    assert nat['seasons']['2025']['duke-blue-devils']['round']=='Final Four'
    assert nat['seasons']['2021']['vcu-rams']['tournament']=='NCAA'
    assert 'No contest' in nat['seasons']['2021']['vcu-rams']['result']
    assert [x['year'] for x in awards['programs']['duke-blue-devils']['NCAA championships']]==[2015,2010,2001,1992,1991]
    assert awards['seasons']['2025']['duke-blue-devils']['first_team']==['Cooper Flagg']
    assert len(awards['seasons']['2025']['duke-blue-devils']['awards'])==5
    assert any(x['year']==2013 for x in awards['programs']['louisville-cardinals']['Vacated NCAA championships'])
    n=0
    for p in (ROOT/'data/cbb/markets').glob('*.json'):
        data=json.loads(p.read_text());a=read('teams/'+p.name)
        for year,entries in data['games'].items():
            games={g['id']:g for phase in a['seasons'][year]['phases'].values() for g in phase.get('games',[])}
            for gid,line in entries.items():
                g=games[gid]
                if 'spread' in line:
                    m=g['points']-g['opponent_points']+line['spread'];assert line['ats']==('W' if m>0 else 'L' if m<0 else 'P')
                if 'total' in line:
                    m=g['points']+g['opponent_points']-line['total'];assert line['ou']==('O' if m>0 else 'U' if m<0 else 'P')
                n+=1
        for record in data['seasons'].values():assert len(record['ats'])==len(record['ou'])==3 and min(record['ats']+record['ou'])>=0
    assert n>30000
    print('Validated 365 programs, completed tournament seasons, official honors and',n,'market game rows')
if __name__=='__main__':main()
