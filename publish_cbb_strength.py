#!/usr/bin/env python3
"""Publish accessible static CBB strength boards; JS adds sorting and filtering."""
import html,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
E=lambda s:html.escape(str(s),quote=True)
VERSION='20261029-strength-v3'
CONFERENCES={'Atlantic Coast Conference':'ACC','Southeastern Conference':'SEC','Atlantic 10 Conference':'A-10','American Conference':'AAC','Atlantic Sun Conference':'ASUN','Coastal Athletic Association':'CAA','Conference USA':'CUSA','Metro Conference':'MAAC','Mid-American Conference':'MAC','Mid-Eastern Athletic Conference':'MEAC','Missouri Valley Conference':'MVC','Northeast Conference':'NEC','Ohio Valley Conference':'OVC','Southern Conference':'SoCon','Southwestern Athletic Conference':'SWAC','United Athletic Conference':'UAC','West Coast Conference':'WCC'}
def conference_name(value):
 return CONFERENCES.get(value,(value or '—').replace(' Conference','').replace(' League',''))
def publish():
 data=json.loads((ROOT/'data/cbb/strength-rankings.json').read_text());page=ROOT/'cbb/rankings/index.html';template=page.read_text()
 template=re.sub(r'<!--CBB_STRENGTH_START-->.*?<!--CBB_STRENGTH_END-->','@@BOARD@@',template,flags=re.S)
 if '@@BOARD@@' not in template:template=re.sub(r'<section class="rank-placeholder".*?</section>','@@BOARD@@',template,flags=re.S)
 if '@@BOARD@@' not in template:raise ValueError('Missing CBB board insertion point')
 template=re.sub(r'<div class="nba-rank-season-control">.*?</div>','',template,flags=re.S)
 template=re.sub(r'<script src="/cbb/rankings/strength.js[^>]*></script>','',template)
 template=re.sub(r'<link rel="stylesheet" href="/cbb/rankings/strength.css[^"]*">','',template)
 template=template.replace('</head>',f'<link rel="stylesheet" href="/cbb/rankings/strength.css?v={VERSION}"><script src="/cbb/rankings/strength.js?v={VERSION}" defer></script></head>')
 updated=datetime.fromisoformat(data['updated_at']).astimezone(ZoneInfo('America/New_York')).strftime('%b %d, %Y · %I:%M %p ET')
 method='<details class="strength-methodology"><summary>About BetWise CBB Team Strength</summary><p>Our proprietary rankings evaluate opponent-adjusted performance, schedule strength and recent form. Preseason rankings provide a starting point and gradually fade as teams play. Strength averages 50.0 across Division I; positive SD values indicate above-average teams and negative values indicate below-average teams. Updated daily using verified results.</p></details>'
 sources='<p class="nba-rank-source">Opening ranking sources: '+ ' · '.join(f'<a href="{E(s["url"])}" target="_blank" rel="noopener">{E(s["name"])}</a>' for s in data['sources'])+'. Game data: ESPN final box scores. </p>'
 columns=[('rank','Rank','Overall rank, or the selected offensive/defensive rank. #1 is strongest.'),('logo','',''),('name','Team',''),('conference','Conference',''),('record','Record','Verified completed games, including non-D1 opponents; exhibitions excluded.'),('rating','Strength','Overall strength index: the average D1 team is 50.0, and ten points represent one standard deviation. Higher is stronger.'),('sd','SD','Standard deviations above or below the Division I mean. Positive is above average; negative is below average.'),('change','Change','Rank movement since the previous published Eastern date. Positive means moved up.'),('offense','Adj. Offense','Points scored per 100 possessions, adjusted for the opposing defense and site. Higher is stronger.'),('defense','Adj. Defense','Points allowed per 100 possessions, adjusted for the opposing offense and site. Lower is stronger.'),('sos','SOS Rank','Schedule difficulty based on opponents faced. #1 means toughest.'),('games','D1 Games','Completed, verified Division I games used by the model.'),('form','Recent Form','Recent opponent-adjusted team performance.'),('prior','Preseason %','Remaining influence of the preseason starting point.'),('kenpom','Opening KP','KenPom preseason rank in the frozen opening snapshot.'),('torvik','Opening BT','Bart Torvik preseason rank in the frozen opening snapshot.')]
 for mode,path,label in [('overall','cbb/rankings/index.html','Team Strength'),('offense','cbb/rankings/offense/index.html','Offensive Strength'),('defense','cbb/rankings/defense/index.html','Defensive Strength')]:
  eligible=data['teams'] if mode=='overall' else sorted([t for t in data['teams'] if t.get(mode+'_rank')],key=lambda t:t[mode+'_rank'])
  header=''
  for key,title,helptext in columns:
   btn=f'<button type="button" data-sort="{key}">{E(title)}<span class="sort-arrow" aria-hidden="true"> ↕</span></button>' if key not in ('logo','record') else E(title)
   helpbtn=f' <button type="button" class="help-btn" aria-label="Define {E(title)}" aria-expanded="false" data-help="{E(helptext)}">?</button>' if helptext else ''
   header+=f'<th scope="col">{btn}{helpbtn}</th>'
  rows=[]
  def fmt(v,digits=1):return '—' if v is None else f'{v:.{digits}f}'
  for t in eligible:
   rank=t['rank'] if mode=='overall' else t[mode+'_rank'];change=t['rank_change'] if mode=='overall' else None
   values={'rank':rank,'name':t['name'],'conference':conference_name(t['conference']), 'rating':t['strength_score'],'sd':(t['strength_score']-50)/10,'change':change,'offense':t['offensive_rating'],'defense':t['defensive_rating'],'sos':t.get('sos_rank'),'games':t['d1_games'],'form':t['recent_form'],'prior':100*t['preseason_weight'],'kenpom':t['source_ranks']['kenpom'],'torvik':t['source_ranks']['torvik']}
   attrs=' '.join(f'data-{k}="{E(v) if v is not None else ""}"' for k,v in values.items())
   teamurl='/cbb/teams/'+t['slug']+'/'
   cells=[str(rank),f'<a href="{teamurl}" aria-label="{E(t["name"])}"><img src="{E(t["logo"])}" alt="" width="26" height="26" loading="lazy"></a>',f'<a class="nba-rank-team" href="{teamurl}">{E(t["name"])}</a>',E(conference_name(t['conference'])),f'{t["wins"]}–{t["losses"]}',fmt(t['strength_score']),f'{(t["strength_score"]-50)/10:+.2f}',f'{change:+d}' if change else '—',fmt(t['offensive_rating']),fmt(t['defensive_rating']),str(t.get('sos_rank') or '—'),str(t['d1_games']),fmt(t['recent_form']),fmt(100*t['preseason_weight'],0)+'%',str(t['source_ranks']['kenpom']),str(t['source_ranks']['torvik'])]
   rows.append(f'<tr {attrs}>'+''.join(f'<td'+(' class="nba-rank-logo"' if i==1 else '')+f'>{c}</td>' for i,c in enumerate(cells))+'</tr>')
  controls='<div class="strength-controls"><label>Find a team<input id="strength-search" type="search" placeholder="Search schools" autocomplete="off"></label><label>Conference<select id="strength-conference"><option value="">All conferences</option>'+''.join(f'<option value="{E(c)}">{E(c)}</option>' for c in sorted({conference_name(t['conference']) for t in eligible if t['conference']}))+'</select></label><span id="strength-count" aria-live="polite">'+str(len(eligible))+' teams</span></div>'
  table=controls+'<div class="data-table-wrap"><div class="strength-table-scroll" tabindex="0" aria-label="Scrollable CBB rankings"><table class="nba-rank-table" id="strength-table" data-sort="rank"><thead><tr>'+header+'</tr></thead><tbody>'+''.join(rows)+'</tbody></table></div></div>' if eligible else '<div class="strength-empty">Offensive and defensive strength rankings will populate after verified Division I games. <a href="/cbb/rankings/">View the opening overall rankings</a>.</div>'
  board=f'<!--CBB_STRENGTH_START--><div class="strength-summary"><span><strong>{E(data["status"])}</strong> · {len(data["teams"])} D1 teams</span><span>Updated {E(updated)}</span><span>Results through {E(data["data_through"] or "No games played")}</span></div>'+table+method+sources+'<!--CBB_STRENGTH_END-->'
  rendered=template.replace('@@BOARD@@',board)
  rendered=re.sub(r'<h1>.*?</h1>',f'<h1>{E(data["season_label"])} CBB {label} Rankings</h1>',rendered,count=1,flags=re.S)
  rendered=re.sub(r'<p class="page-intro">.*?</p>','<p class="page-intro">BetWise strength rankings use opponent-adjusted performance, seven-game form and a preseason starting point that fades over each team’s first 12 D1 games. Updated daily.</p>',rendered,count=1,flags=re.S)
  rendered=re.sub(r'<nav class="rank-tabs".*?</nav>','<nav class="rank-tabs" aria-label="CBB rankings">'+''.join(f'<a href="{u}"'+(' class="active" aria-current="page"' if m==mode else '')+f'>{l}</a>' for m,u,l in [('overall','/cbb/rankings/','Overall Team Rankings'),('offense','/cbb/rankings/offense/','Offensive Rankings'),('defense','/cbb/rankings/defense/','Defensive Rankings'),('leaders','/cbb/division-one-season-leaders/','Season Leaders')])+'</nav>',rendered,count=1,flags=re.S)
  rendered=re.sub(r'<title>.*?</title>',f'<title>CBB {label} Rankings | BetWise</title>',rendered,count=1)
  rendered=re.sub(r'<link rel="canonical" href="[^"]*">',f'<link rel="canonical" href="https://matchlab.parlaycalculator.bet/{path.removesuffix("index.html")}">',rendered,count=1)
  out=ROOT/path;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(rendered)
 print('Published CBB overall, offensive and defensive strength pages')
if __name__=='__main__':publish()
