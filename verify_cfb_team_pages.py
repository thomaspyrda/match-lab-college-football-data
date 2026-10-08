"""Validate all populated CFB team pages and embedded season sections."""
import json,re
from pathlib import Path
from collections import Counter
from build_cfb_team_pages import slug,schedule as render_schedule
from refresh_cfb_team_details import CATEGORIES
ROOT=Path(__file__).resolve().parent
def main():
 registry=json.loads((ROOT/'data/cfb/team-registry.json').read_text())['teams'];coverage=Counter();count=0
 by_id={str(t['id']):t for t in registry}
 for team in registry:
  page=(ROOT/'cfb/teams'/slug(team['name'])/'index.html').read_text()
  order=['snapshot','coaches','recruiting','schedule','metrics','seasonLeaders']
  positions=[page.index(f'id="{key}"') for key in order];assert positions==sorted(positions)
  d=json.loads(re.search(r'id="teamSeasonData">(.*?)</script>',page,re.S)[1])
  for year,s in d['seasons'].items():
   assert len(s['games'])==s['games_played']==sum(s['record'].values())
   assert set(s['sections'])=={'coachingGrid','recruitingContent','metricsGrid','seasonLeadersContent','seasonResult'}
   assert s['sections']['seasonLeadersContent'].count('season-leader-card')==6
   schedule=s.get('schedule',s['games']);assert len({g['id'] for g in schedule})==len(schedule)
   table=render_schedule(s,by_id)
   for g in schedule:
    for key in ['result','ats','ou']:
     value=g.get(key)
     color='result-w' if value in ['W','O'] else 'result-l' if value in ['L','U'] else 'result-p'
     assert f'class="{color}">{value or "—"}</td>' in table
   assert len({g['id'] for g in s['games']})==len(s['games'])
   for category,p in s['details']['leaders'].items():
    if not p:continue
    assert p['rank']>=1 and p['league_total']>=p['stats'][CATEGORIES[category]]
    coverage[(year,category)]+=1
   for pair in s['details']['metrics']:
    for side in ['offense','defense']:
     if pair.get(side) is not None:assert 1<=pair[side+'_rank']<=pair[side+'_field_size']
   count+=1
 assert len(registry)==138
 print(f'Validated {len(registry)} CFB routes and {count} populated team-seasons.')
 for year in sorted({y for y,c in coverage}):print(year,{c:coverage[(year,c)] for c in CATEGORIES})
if __name__=='__main__':main()
