"""Build regular-season CFB team archives from the complete Match Lab source,
including Week 1 and FCS opponents. Pregame profiles are not season totals.
"""
import html, json, re
from cfb_program_accolades import render as program_accolades
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE='https://matchlab.parlaycalculator.bet'
FIRST=2015
def esc(v): return html.escape(str(v),quote=True)
def slug(v): return re.sub(r'[^a-z0-9]+','-',v.lower()).strip('-')
def number(v):
 if v is None:return None
 try:return float(v)
 except (ValueError,TypeError):return None
def record(rows):
 return {'wins':sum(g['result']=='W' for g in rows),'losses':sum(g['result']=='L' for g in rows),'ties':sum(g['result']=='T' for g in rows)}
def record_label(r):
 return f"{r['wins']}-{r['losses']}"+(f"-{r['ties']}" if r['ties'] else '')
def market_record(rows,key):
 values=[g[key] for g in rows if g[key] is not None]
 labels=['W','L','P'] if key=='ats' else ['O','U','P']
 return {'first':values.count(labels[0]),'second':values.count(labels[1]),'pushes':values.count(labels[2]),'games':len(values)}

def build_season(games, year, now=None):
 now=now or datetime.now(timezone.utc)
 by_team=defaultdict(list);fbs=set();seen=set()
 for g in games:
  gid=str(g['game_id'])
  if gid in seen:raise ValueError(f'Duplicate game {year}: {gid}')
  seen.add(gid)
  for side in ['home','away']:
   if (g.get(side+'_profile') or {}).get('classification')=='FBS':fbs.add(str(g[side+'_id']))
  result=g.get('result')
  if not result:continue
  hp=number(result.get('home_points'));ap=number(result.get('away_points'))
  if hp is None or ap is None:continue
  date=g.get('start_date')
  if not date:raise ValueError(f'Missing kickoff {gid}')
  if datetime.fromisoformat(date.replace('Z','+00:00'))>now:raise ValueError(f'Future game marked complete {gid}')
  home_spread=number(g.get('spread'));total=number(g.get('over_under'))
  for side,opp in [('home','away'),('away','home')]:
   tid=str(g[side+'_id']);pf,pa=(hp,ap) if side=='home' else (ap,hp)
   spread=home_spread if side=='home' else (-home_spread if home_spread is not None else None)
   ats=None if spread is None else ('W' if pf+spread>pa else 'L' if pf+spread<pa else 'P')
   ou=None if total is None else ('O' if pf+pa>total else 'U' if pf+pa<total else 'P')
   by_team[tid].append({'id':gid,'week':g['week'],'date':date,'team_name':g[side],
    'conference':g.get(side+'_conference'),'opponent':g[opp],'opponent_id':str(g[opp+'_id']),
    'conference_game':bool(g.get('conference_game')),
    'site':'N' if g.get('neutral_site') else 'H' if side=='home' else 'A',
    'result':'W' if pf>pa else 'L' if pf<pa else 'T','points':pf,'allowed':pa,
    'spread':spread,'total':total,'ats':ats,'ou':ou,'provider':g.get('provider'),
    'market_closing_verified':False})
 seasons={}
 for tid in fbs:
  rows=sorted(by_team.get(tid,[]),key=lambda g:(g['date'],g['id']))
  if not rows:continue
  n=len(rows)
  seasons[tid]={'year':year,'season_type':'regular','coverage':'source_regular_season',
   'name':rows[-1]['team_name'],'conference':rows[-1]['conference'],
   'record':record(rows),'games_played':n,'ppg':sum(g['points'] for g in rows)/n,
   'ppg_allowed':sum(g['allowed'] for g in rows)/n,
   'home':record([g for g in rows if g['site']=='H']),
   'away':record([g for g in rows if g['site']=='A']),
   'neutral':record([g for g in rows if g['site']=='N']),
   'conference_record':record([g for g in rows if g['conference_game']]),
   'ats':market_record(rows,'ats'),'ou':market_record(rows,'ou'),'games':rows,
   'sources':[{'name':'CollegeFootballData regular-season games and lines',
     'url':BASE+f'/data/historical/{year}.json'}]}
 for tid,s in seasons.items():
  s['ppg_rank']=1+sum(other['ppg']>s['ppg'] for other in seasons.values())
  s['ppg_allowed_rank']=1+sum(other['ppg_allowed']<s['ppg_allowed'] for other in seasons.values())
  s['rank_field_size']=len(seasons)
 return seasons

def snapshot(s):
 if not s:return '<p class="archive-note">No FBS regular-season archive is loaded for this season. Earlier FCS seasons are outside this archive.</p>'
 values=[('Record',record_label(s['record'])),('PPG',f"{s['ppg']:.1f}"),
  ('PPG Allowed',f"{s['ppg_allowed']:.1f}"),('Home',record_label(s['home'])),('Away',record_label(s['away'])),('Neutral',record_label(s['neutral'])),
  ('Conference',record_label(s['conference_record'])),('Games',s['games_played'])]
 for key,label in [('ats','ATS · W-L-P'),('ou','O/U · O-U-P')]:
  m=s[key];values.append((label,f"{m['first']}-{m['second']}-{m['pushes']}" if m['games'] else '—'))
 return ''.join(f'<article class="snapshot-card"><b>{esc(v)}</b><span>{esc(k)}</span></article>' for k,v in values)

def schedule(s,registry):
 if not s:return '<tr><td colspan="10">No verified regular-season results loaded.</td></tr>'
 rows=[]
 for g in s.get('schedule',s['games']):
  opp=registry.get(g['opponent_id']);name=esc(g['opponent'])
  if opp:name=f'<a href="{BASE}/cfb/teams/{slug(opp["name"])}/">{name}</a>'
  spread='—' if g['spread'] is None else f"{g['spread']:+g}"
  total='—' if g['total'] is None else f"{g['total']:g}"
  from cfb_team_sections import cls
  score='—' if g['points'] is None else f"{g['points']:g}–{g['allowed']:g}"
  vals=['Post' if g.get('season_type')=='postseason' else g['week'],g['date'][:10],g['site'],name,g['result'] or '—',score,spread,g['ats'] or '—',total,g['ou'] or '—']
  rows.append('<tr>'+''.join(f'<td class="{cls(v) if i in [4,7,9] else ""}">{v if i==3 else esc(v)}</td>' for i,v in enumerate(vals))+'</tr>')
 return ''.join(rows)

def notes(s):
 if not s:return 'Select another season to view available FBS results.'
 return (f"{s['year']} regular season · {s['games_played']} completed games · {esc(s['conference'] or 'Conference unavailable')}. "
  f"Postseason and bowls are excluded. Scoring ranks compare {s['rank_field_size']} FBS teams with recorded results: "
  f"PPG #{s['ppg_rank']}; PPG allowed #{s['ppg_allowed_rank']}. "
  f"ATS coverage {s['ats']['games']}/{s['games_played']}; totals coverage {s['ou']['games']}/{s['games_played']}. "
  'Betting lines are source-reported; closing status and observation timestamps are not verified. Missing lines are excluded from market records. '
  f'<a href="{s["sources"][0]["url"]}">View source data</a>.')

def page(team,seasons,registry,current):
 default=current if str(current) in seasons else max(map(int,seasons),default=current)
 s=seasons.get(str(default));section=(s or {}).get('sections',{});name=team['name'];path=f'/cfb/teams/{slug(name)}/'
 options=''.join(f'<option value="{y}"{" selected" if y==default else ""}>{y}{" · no FBS data" if str(y) not in seasons else ""}</option>' for y in range(current,FIRST-1,-1))
 payload=json.dumps({'team':team,'seasons':seasons},separators=(',',':')).replace('<','\\u003c')
 robots='index,follow' if seasons else 'noindex,follow'
 logo_tile_variant = ' team-hero-logo-wrap--dark-gray' if str(team['id']) in {'2132', '2294', '154'} else ''
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)} Stats &amp; Season History | BetWise CFB</title><meta name="description" content="{esc(name)} college football season records, coaches, recruiting ranks, advanced metrics, player leaders and schedule results from 2015 forward."><meta name="robots" content="{robots}"><link rel="canonical" href="{BASE}{path}">
<link rel="stylesheet" href="/cfb-dashboard-preview/styles.css?v=27"><link rel="stylesheet" href="/cfb/team-page.css?v=logo-tiles-20261009"><link rel="stylesheet" href="/site-navigation.css?v=2"><script src="/site-navigation-v3.js" defer></script><script id="team-color-script" src="https://matchlab.parlaycalculator.bet/sports-research/team-theme.js?v=2" defer></script><style id="team-section-title-style">.team-section:not(#snapshot) .team-section-head h2{{display:none!important}}</style></head>
<body class="team-page"><header class="site-header"><div class="header-inner"><a class="betwise-brand" href="https://parlaycalculator.bet/"><img src="/assets/betwise-logo.png" alt="BetWise" width="240" height="240"></a><nav class="site-nav" aria-label="Primary navigation"><a href="/cfb-dashboard-preview/">CFB Dashboard</a><a href="/teams.html">CFB Teams</a></nav><details class="mobile-menu"><summary aria-label="Open navigation menu">Menu</summary><nav aria-label="Mobile navigation"><a href="/cfb-dashboard-preview/">CFB Dashboard</a><a href="/teams.html">CFB Teams</a></nav></details></div></header>
<main class="team-shell"><section class="team-hero"><div class="team-hero-logo-wrap{logo_tile_variant}"><img class="team-hero-logo" src="https://a.espncdn.com/i/teamlogos/ncaa/500/{team['id']}.png" alt="{esc(name)} logo"></div><div class="team-hero-copy"><p class="team-kicker">CFB TEAM RESEARCH · {esc(team['conference'])}</p><h1>{esc(name)}</h1><p>Season leadership, recruiting classes, advanced metrics, player leaders and results.</p><div class="season-control"><label for="seasonSelect">Season</label><select id="seasonSelect" aria-label="Choose {esc(name)} season">{options}</select></div></div></section>
<nav class="team-subnav" aria-label="Team sections"><a href="#snapshot">Snapshot</a><a href="#coaches">Leadership</a><a href="#recruiting">Recruiting Class</a><a href="#schedule">Schedule</a><a href="#metrics">Metrics</a><a href="#seasonLeaders">Players</a><a href="#programAccolades">Accolades</a><a href="/teams.html">All CFB Teams</a></nav>
<section id="snapshot" class="team-section"><div class="team-section-head"><p>SEASON SNAPSHOT</p><h2 id="snapshotTitle">{default} regular season</h2></div><div id="snapshotGrid" class="snapshot-grid">{snapshot(s)}</div><p id="seasonNote" class="archive-note">{notes(s)}</p><div id="seasonResult">{section.get("seasonResult","")}</div></section>
<section id="coaches" class="team-section"><div class="team-section-head"><p>SEASON LEADERSHIP</p><h2>Coaching staff</h2></div><div id="coachingGrid" class="coaching-grid">{section.get("coachingGrid","")}</div></section>
<section id="recruiting" class="team-section"><div class="team-section-head"><p>RECRUITING CLASS</p><h2>Incoming signing class</h2></div><div id="recruitingContent">{section.get("recruitingContent","")}</div></section>
<section id="schedule" class="team-section"><div class="team-section-head"><p>FULL SEASON SCHEDULE</p><h2>Results and market lines</h2></div><div class="schedule-wrap"><table class="team-schedule"><thead><tr><th>Wk</th><th>Date</th><th>Site</th><th>Opponent</th><th>Result</th><th>Score</th><th>Spread</th><th>ATS</th><th>Total</th><th>O/U</th></tr></thead><tbody id="scheduleBody">{schedule(s,registry)}</tbody></table></div><p class="archive-note">H = home · A = away · N = neutral · Post = postseason. Source-reported spreads and totals; unverified closing status. Conference championships follow the source's regular-season classification.</p></section>
<section id="metrics" class="team-section"><div class="team-section-head"><p>ADVANCED METRICS</p><h2>Offense and defense</h2></div><div id="metricsGrid" class="team-metrics-grid">{section.get("metricsGrid","")}</div></section>
<section id="seasonLeaders" class="team-section"><div class="team-section-head"><p>SEASON LEADERS</p><h2>Players who led the team</h2></div><div id="seasonLeadersContent">{section.get("seasonLeadersContent","")}</div></section>

{program_accolades(team["id"])}
<p class="archive-note">Sources: <a href="https://collegefootballdata.com/">CollegeFootballData</a>; logos and team identity: ESPN. Historical conferences follow each season's game records.</p></main><footer>BetWise CFB research tools</footer>
<script type="application/json" id="teamSeasonData">{payload}</script><script src="/cfb/team-page.js?v=2" defer></script></body></html>'''

RANKING_LINKS="<section class=\"ranking-links\" aria-labelledby=\"rankingLinksTitle\">\n        <p id=\"rankingLinksTitle\" class=\"ranking-links-label\">Explore CFB Rankings</p>\n        <div class=\"ranking-links-grid\">\n          <a href=\"https://matchlab.parlaycalculator.bet/college-football-team-strength-rankings/\">Team Strength</a>\n          <a href=\"https://matchlab.parlaycalculator.bet/college-football-strength-of-schedule-rankings/\">SOS Rankings</a>\n          <a href=\"https://matchlab.parlaycalculator.bet/college-football-offensive-strength-rankings/\">Offensive Strength</a>\n          <a href=\"https://matchlab.parlaycalculator.bet/college-football-defensive-strength-rankings/\">Defensive Strength</a>\n        </div>\n      </section>"
RANKING_STYLE="<link rel=\"stylesheet\" href=\"/sports-research/rankings-navigation.css?v=2\">"

def main():
 teams=json.loads((ROOT/'data/cfb/team-registry.json').read_text())['teams'];registry={str(t['id']):t for t in teams}
 assert len(registry)==len(teams)==138
 paths=sorted((ROOT/'data/historical').glob('*.json'));assert paths,'No historical source files'
 current=max(int(p.stem) for p in paths);histories={tid:{} for tid in registry}
 for path in paths:
  year=int(path.stem)
  if year<FIRST:continue
  d=json.loads(path.read_text());assert d['season']==year
  rows=build_season(d['games'],year)
  detail_path=ROOT/'data/cfb/details'/f'{year}.json'
  if detail_path.exists():
   from cfb_team_sections import attach_details
   rows=attach_details(rows,json.loads(detail_path.read_text()),registry,build_season,current)
  for tid,s in rows.items():
   if tid in registry:histories[tid][str(year)]=s
 for tid,seasons in histories.items():
  for season in seasons.values():
   for game in season['games']:
    opponent=registry.get(game['opponent_id'])
    if opponent:game['opponent_url']=BASE+f'/cfb/teams/{slug(opponent["name"])}/'
 for tid,team in registry.items():
  out=ROOT/'cfb/teams'/slug(team['name']);out.mkdir(parents=True,exist_ok=True)
  (out/'index.html').write_text(page(team,histories[tid],registry,current))
  data=ROOT/'data/cfb/teams'/f'{tid}.json';data.parent.mkdir(parents=True,exist_ok=True)
  data.write_text(json.dumps({'schema_version':1,'team_id':f'cfb:cfbd:{tid}','seasons':histories[tid]},separators=(',',':')))
 directory=ROOT/'teams.html'
 if directory.exists():
  content=directory.read_text()
  content=re.sub(r'<section class="ranking-links".*?</section>','',content,flags=re.S)
  ranking_anchor=r'<a href="https://matchlab[.]parlaycalculator[.]bet/college-football-team-strength-rankings/">View all Team Strength rankings →</a>'
  if re.search(ranking_anchor,content):content=re.sub(ranking_anchor,lambda m:RANKING_LINKS,content,count=1)
  else:content=content.replace('</section><nav class="directory-jumps"',RANKING_LINKS+'</section><nav class="directory-jumps"',1)
  if 'rankings-navigation.css' not in content:content=content.replace('</head>',RANKING_STYLE+'</head>',1)
  if 'team-card-hover.css' not in content:content=content.replace('</head>','<link rel="stylesheet" href="/sports-research/team-card-hover.css?v=1"></head>',1)
  def link(m):
   body=m.group(1);idmatch=re.search(r'/([0-9]+)\.png',body)
   if not idmatch or idmatch[1] not in registry:return m.group(0)
   team=registry[idmatch[1]]
   return f'<a class="conference-team" style="color:inherit;text-decoration:none" href="{BASE}/cfb/teams/{slug(team["name"])}/">{body}</a>'
  content=re.sub(r'<article class="conference-team">(.*?)</article>',link,content,flags=re.S)
  content=content.replace('Individual team research pages will be added to this directory as they become available.','Open a team to explore regular-season records, scoring and schedules from 2015 forward.')
  directory.write_text(content)
 urls=[BASE+'/teams.html']+[BASE+f'/cfb/teams/{slug(t["name"])}/' for tid,t in registry.items() if histories[tid]]
 (ROOT/'sitemap-cfb-teams.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{esc(u)}</loc></url>' for u in urls)+'</urlset>')
 sm=ROOT/'sitemap.xml'
 if sm.exists():
  content=sm.read_text()
  if 'sitemap-cfb-teams.xml' not in content:sm.write_text(content.replace('</sitemapindex>',f'<sitemap><loc>{BASE}/sitemap-cfb-teams.xml</loc></sitemap></sitemapindex>'))
 print(f'Built {len(teams)} CFB pages, {sum(len(s) for s in histories.values())} team-seasons from {FIRST}–{current}')
if __name__=='__main__':main()
