#!/usr/bin/env python3
"""Publish accessible static CBB strength boards; JS adds sorting and filtering."""
import html,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
E=lambda s:html.escape(str(s),quote=True)
VERSION='20261029-strength-v1'
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
 method='''<details class="strength-methodology"><summary>How BetWise CBB Team Strength works</summary>
 <h3>Opening rankings</h3><p>The frozen October 29, 2026 starting order averages KenPom and Bart Torvik preseason ranks equally. A lower average ranks higher; ties use KenPom rank. These sources establish the starting point only and are not refreshed by our daily formula.</p>
 <h3>Our performance formula</h3><p>Offensive and defensive efficiency use points per 100 estimated possessions. Possessions average both teams’ FGA − offensive rebounds + turnovers + 0.475 × free-throw attempts. Offense adjusts for the opponent’s defensive strength; defense adjusts for its offensive strength. Opponent ratings are frozen before each Eastern game day and use only earlier results. Home advantage is set initially at four net points per 100 possessions; neutral sites receive no adjustment. There is no additional SOS bonus, poll bonus, market input or separate D1 loss penalty.</p>
 <h3>Seven-game form and twelve-game transition</h3><p>The latest seven D1 performances receive weights of 1.60, 1.50, 1.40, 1.30, 1.20, 1.10 and 1.05, newest first. All earlier games receive 1.00. Preseason influence equals max(0, 1 − completed D1 games ÷ 12). After game 12, only our performance formula remains. Teams with fewer than seven games use the games available.</p>
 <h3>Rating scale and preseason units</h3><p>The underlying rating is adjusted offensive efficiency minus adjusted defensive efficiency, less non-D1 penalties. The displayed Strength index is standardized across D1 teams to an average of 50.0 and a standard deviation of 10; it is not a win probability or predicted spread. To turn the average preseason rank into a numerical starting value, we use its normal percentile score multiplied by 10. Internally, that starting value is split equally between offense and defense around a neutral 105-point efficiency baseline. This is an initialization assumption, not an observed offensive or defensive statistic. Separate unit ratings and schedule strength are shown only after verified D1 games.</p>
 <h3>Non-D1 opponents</h3><p>Exhibitions are excluded. Verified non-D1 games do not enter efficiency, form or the 12-game count. A win by 15+ earns no bonus and no penalty. Wins by 11–14 deduct 0.5 rating points; wins by 6–10 deduct 1.0; wins by 1–5 deduct 2.0. A loss deducts 3.0 plus 0.1 per point of defeat, capped at 6.0 per game. Penalties accumulate and apply to overall strength only, including during the preseason transition.</p>
 <h3>Daily publication</h3><p>Updates run daily at 8 a.m. Eastern with the prior Eastern game day’s verified final results, including D1 postseason games. Daily snapshots are archived. Missing or inconsistent final boxes block an update and preserve the last published list. These initial model parameters have functional checks; they have not yet been optimized through historical predictive backtesting.</p></details>'''
 sources='<p class="nba-rank-source">Opening ranking sources: '+ ' · '.join(f'<a href="{E(s["url"])}" target="_blank" rel="noopener">{E(s["name"])}</a>' for s in data['sources'])+'. Game data: ESPN final box scores. <a href="/data/cbb/strength-rankings.json">Download current rankings</a>.</p>'
 columns=[('rank','Rank','Overall rank, or the selected offensive/defensive rank. #1 is strongest.'),('logo','',''),('name','Team',''),('conference','Conference',''),('record','Record','Verified completed games, including non-D1 opponents; exhibitions excluded.'),('rating','Strength','Overall strength index: the average D1 team is 50.0, and ten points represent one standard deviation. Higher is stronger.'),('change','Change','Rank movement since the previous published Eastern date. Positive means moved up.'),('offense','Adj. Offense','Points scored per 100 possessions, adjusted for the opposing defense and site. Higher is stronger.'),('defense','Adj. Defense','Points allowed per 100 possessions, adjusted for the opposing offense and site. Lower is stronger.'),('sos','SOS Rank','Average opponents’ overall efficiency at the time of each game. #1 means toughest; no additional overall strength bonus.'),('games','D1 Games','Completed, verified Division I games used by the model.'),('form','Recent Form','Adjusted net efficiency in the latest seven D1 games, with the same recency weights. This is a subset of the season model, not an extra additive bonus.'),('prior','Preseason %','Remaining influence of the frozen starting rating. Reaches zero after the twelfth D1 game.'),('kenpom','Opening KP','KenPom preseason rank in the frozen opening snapshot.'),('torvik','Opening BT','Bart Torvik preseason rank in the frozen opening snapshot.')]
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
   values={'rank':rank,'name':t['name'],'conference':t['conference'] or '', 'rating':t['strength_score'],'change':change,'offense':t['offensive_rating'],'defense':t['defensive_rating'],'sos':t.get('sos_rank'),'games':t['d1_games'],'form':t['recent_form'],'prior':100*t['preseason_weight'],'kenpom':t['source_ranks']['kenpom'],'torvik':t['source_ranks']['torvik']}
   attrs=' '.join(f'data-{k}="{E(v) if v is not None else ""}"' for k,v in values.items())
   teamurl='/cbb/teams/'+t['slug']+'/'
   cells=[str(rank),f'<a href="{teamurl}" aria-label="{E(t["name"])}"><img src="{E(t["logo"])}" alt="" width="26" height="26" loading="lazy"></a>',f'<a class="nba-rank-team" href="{teamurl}">{E(t["name"])}</a>',E(t['conference'] or '—'),f'{t["wins"]}–{t["losses"]}',fmt(t['strength_score']),f'{change:+d}' if change else '—',fmt(t['offensive_rating']),fmt(t['defensive_rating']),str(t.get('sos_rank') or '—'),str(t['d1_games']),fmt(t['recent_form']),fmt(100*t['preseason_weight'],0)+'%',str(t['source_ranks']['kenpom']),str(t['source_ranks']['torvik'])]
   rows.append(f'<tr {attrs}>'+''.join(f'<td'+(' class="nba-rank-logo"' if i==1 else '')+f'>{c}</td>' for i,c in enumerate(cells))+'</tr>')
  controls='<div class="strength-controls"><label>Find a team<input id="strength-search" type="search" placeholder="Search schools" autocomplete="off"></label><label>Conference<select id="strength-conference"><option value="">All conferences</option>'+''.join(f'<option value="{E(c)}">{E(c)}</option>' for c in sorted({t['conference'] for t in eligible if t['conference']}))+'</select></label><span id="strength-count" aria-live="polite">'+str(len(eligible))+' teams</span></div>'
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
