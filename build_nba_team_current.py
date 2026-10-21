"""Publish all 30 current team summaries without modifying historical archives."""
import json
from collections import defaultdict
from pathlib import Path
from build_nba_team_rankings import TEAM_INFO, METRIC_LABELS, LOWER_IS_BETTER, make_ranks
from nba_current_rankings import build_current_rows, ratio

ROOT = Path(__file__).resolve().parent
YEAR = 2027

def build(cache, registry):
    rows, coverage = build_current_rows(cache, registry, TEAM_INFO, YEAR, METRIC_LABELS)
    teams = {str(t['espn_id']):t['slug'] for t in registry['teams'] if t['sport']=='nba'}
    selected = {str(g['id']):g for g in cache['games'] if g['season']==YEAR and g['phase']==2}
    players = defaultdict(dict)
    keys = {'points':'points','rebounds':'rebounds','assists':'assists','steals':'steals','blocks':'blocks','turnovers':'turnovers','minutes':'minutes','fgm':'fg_made','fga':'fg_attempts','tpm':'three_made','tpa':'three_attempts','ftm':'ft_made','fta':'ft_attempts'}
    for g in selected.values():
        for tid, appearances in g.get('players',{}).items():
            seen = set()
            for p in appearances:
                if not p.get('minutes') or p['minutes']<=0: continue
                if p['id'] in seen: raise ValueError('Duplicate player appearance')
                seen.add(p['id'])
                r = players[teams[tid]].setdefault(p['id'],dict(id=p['id'],name=p['name'],position=p.get('position'),games=0,totals=defaultdict(float),coverage=defaultdict(int)))
                r['games']+=1
                for raw,key in keys.items():
                    if p.get(raw) is not None:
                        r['totals'][key]+=p[raw];r['coverage'][key]+=1
    cats={'points':'points','rebounds':'rebounds','assists':'assists','steals':'steals','blocks':'blocks','threes':'three_made'}
    league=defaultdict(lambda:defaultdict(float))
    for roster in players.values():
        for p in roster.values():
            p['totals']={k:v for k,v in p['totals'].items() if p['coverage'][k]==p['games']}
            del p['coverage']
            p['per_game']={k:v/p['games'] for k,v in p['totals'].items()}
            t=p['totals'];m=p['per_game']
            for pct,a,b in [('fg_pct','fg_made','fg_attempts'),('three_pct','three_made','three_attempts'),('ft_pct','ft_made','ft_attempts')]:
                m[pct]=ratio(t.get(a,0),t.get(b,0),1) if a in t and b in t else None
            m['threes']=m.get('three_made')
            for cat,key in cats.items():
                if key in t: league[p['id']][cat]+=t[key]
    result={}
    for row in rows:
        slug=row['slug'];m=row['metrics'];m['points_allowed_per_game']=m.get('ppg_allowed')
        games=[g for g in selected.values() if any(teams[tid]==slug for tid in g['teams'])]
        record={'overall':row['record']}
        for venue in ('home','away'):
            subset=[g for g in games if not g.get('neutral') and ((teams[g['home']]==slug)==(venue=='home'))]
            wins=sum(next(b['points'] for tid,b in g['teams'].items() if teams[tid]==slug)>next(b['points'] for tid,b in g['teams'].items() if teams[tid]!=slug) for g in subset)
            record[venue]=f'{wins}–{len(subset)-wins}'
        roster=list(players[slug].values())
        leaders={}
        for cat,key in cats.items():
            eligible=[p for p in roster if p['totals'].get(key,0)>0]
            leaders[cat]=[p['id'] for p in sorted(eligible,key=lambda p:(-p['totals'][key],-p['per_game'][key],p['name']))[:1]]
        for p in roster:
            p['league_totals']=dict(league[p['id']]);p['league_ranks']={cat:1+sum(v.get(cat,0)>league[p['id']].get(cat,0) for v in league.values()) for cat in cats}
        result[slug]={'key':str(YEAR),'label':'2026–27','coverage':'season_to_date','metrics':m,'record':record,'players':roster,'leaders':leaders,'games_played':row['games_played'],'playoff_result':'Season in progress','ranks':{k:make_ranks(rows,k,k not in LOWER_IS_BETTER)[slug] for k in m}}
    return {'season':YEAR,**coverage,'teams':result}

if __name__=='__main__':
    output=build(json.loads((ROOT/'nba/dashboard/data/completed-games.json').read_text()),json.loads((ROOT/'data/sports/team-registry.json').read_text()))
    (ROOT/'nba/teams/data/current-season.json').write_text(json.dumps(output,ensure_ascii=False,separators=(',',':'))+'\n')
    print(f"Updated {len(output['teams'])} team pages from {output['completed_games']} completed games")
