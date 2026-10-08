"""Refresh full-FBS leaders from completed regular-season player box scores."""
import json,math,argparse
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
from refresh_cfb_team_details import api,canon,num,FIELDS
from leaderboard_core import derived,categories,tables
ROOT=Path(__file__).resolve().parent
EXTRA={'fg_made':['kicking:FGM'],'fg_att':['kicking:FGA'],'kicking_points':['kicking:PTS'],'punt_att':['punting:NO'],'punt_yards':['punting:YDS'],'punt_return_yards':['puntreturns:YDS'],'kick_return_yards':['kickreturns:YDS']}
def aggregate(boxes,completed,fbs):
 players={};seen=set();unique=set();fields={k:aliases for group in FIELDS.values() for k,aliases in group};fields.update(EXTRA)
 for box in boxes:
  gid=str(box['id'])
  if gid not in completed:continue
  seen.add(gid)
  for tr in box.get('teams',[]):
   team=canon(tr.get('team'))
   if team not in fbs:continue
   gameplayers={}
   for c in tr.get('categories',[]):
    for st in c.get('types',[]):
     key=str(c['name']).lower()+':'+str(st['name']).upper()
     for a in st.get('athletes',[]):
      pid=str(a['id']);u=(gid,team,pid,key)
      if u in unique:raise ValueError('Duplicate game/player/stat record')
      unique.add(u);q=gameplayers.setdefault(pid,dict(name=a['name'],raw={}));q['raw'][key]=a['stat']
   for pid,q in gameplayers.items():
    p=players.setdefault(pid,dict(id=pid,name=q['name'],teams=set(),games=set(),stats=defaultdict(float)))
    p['teams'].add(team);p['games'].add(gid);raw=q['raw']
    for key,aliases in fields.items():
     value=next((num(raw[a]) for a in aliases if num(raw.get(a)) is not None),None)
     if value is not None:p['stats'][key]+=value
    if 'kicking:FG' in raw and '/' in str(raw['kicking:FG']):
     made,att=map(float,raw['kicking:FG'].split('/'));p['stats']['fg_made']+=made;p['stats']['fg_att']+=att
    if 'kicking:PTS' not in raw:
     made=num(raw.get('kicking:FGM')) or (float(str(raw['kicking:FG']).split('/')[0]) if 'kicking:FG' in raw else 0);xp=num(raw.get('kicking:XPM')) or (float(str(raw['kicking:XP']).split('/')[0]) if 'kicking:XP' in raw else 0);p['stats']['kicking_points']+=3*made+xp
    if 'passing:C/ATT' in raw and not any(k in raw for k in ['passing:ATT','passing:ATTEMPTS']):
     cmp,att=raw['passing:C/ATT'].split('/');p['stats']['completions']+=float(cmp);p['stats']['attempts']+=float(att)
 if seen!=set(completed):raise ValueError(f'Missing player box scores for {len(set(completed)-seen)} completed games')
 for p in players.values():p['games_played']=len(p['games']);derived(p,college=True)
 return list(players.values())
def render(p):
 from build_seo_pages import page_shell,ranking_tabs,ranking_hero,team_archive_link
 body=f'''<p class="eyebrow">BETWISE CFB · LIVE DATA</p><h1>{p['season']} FBS Season Leaders</h1><p class="page-intro">Top 10 FBS players in totals, per-game production and efficiency, through completed regular-season games in Week {p['through_week']}.</p>{ranking_hero()}{ranking_tabs('leaders')}<p class="note">GP counts games with a player box-score record. Zero-stat appearances can be absent from this feed, so averages reflect recorded appearances. Qualification thresholds appear on each rate table.</p>{tables(p,team_archive_link)}<p class="note">FBS players only, including games against FCS teams. Postseason and unfinished games are excluded. Ties share ranks; relevant secondary statistics order ties. Updated {p['as_of']}. <a href="https://collegefootballdata.com">Source: CollegeFootballData</a>.</p>'''
 html=page_shell(f'{p["season"]} FBS Season Leaders | BetWise','FBS player leaders in season totals, averages per game and efficiency.','https://matchlab.parlaycalculator.bet/college-football-season-leaders/',body);html=html.replace('</head>','<link rel="stylesheet" href="/sports-research/season-leaders.css?v=1"></head>');dest=ROOT/'college-football-season-leaders/index.html';dest.parent.mkdir(exist_ok=True);dest.write_text(html)
def build(year):
 rows,_=api('/games',year=year,seasonType='regular',classification='fbs');fbs={canon(t['name']) for t in json.loads((ROOT/'data/cfb/team-registry.json').read_text())['teams']}
 completed={str(g['id']):g for g in rows if g.get('completed') and g.get('homePoints') is not None and g.get('awayPoints') is not None};boxes=[];weeks=sorted({g['week'] for g in completed.values()})
 if not weeks:raise ValueError('No completed regular-season games')
 for week in weeks:
  box,_=api('/games/players',year=year,week=week,seasonType='regular',classification='fbs');boxes.extend(box)
 players=aggregate(boxes,completed,fbs);played=defaultdict(int)
 for g in completed.values():
  for side in ['homeTeam','awayTeam']:
   team=canon(g[side])
   if team in fbs:played[team]+=1
 minimum=max(1,math.ceil(max(played.values())/2));p=dict(season=year,as_of=datetime.now(timezone.utc).isoformat(),through_week=max(weeks),completed_game_ids=sorted(completed),fbs_teams=len(fbs),players=len(players),categories=categories(players,minimum,college=True))
 if not any(c['players'] for c in p['categories']):raise ValueError('No leader records')
 (ROOT/'data/cfb-season-leaders.json').write_text(json.dumps(p,indent=2)+'\n');render(p);print(f'{len(players)} FBS players, {len(completed)} games, {len(p["categories"])} categories')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--season',type=int,default=2026);args=a.parse_args();build(args.season)
