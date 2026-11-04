#!/usr/bin/env python3
"""Publish accessible static CBB strength boards; JS adds sorting and filtering."""
import html,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
E=lambda s:html.escape(str(s),quote=True)
VERSION='20261104-ranking-scrollbars'
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
 columns=[('rank','Rank','Overall rank, or the selected offensive/defensive rank. #1 is strongest.'),('logo','',''),('name','Team',''),('conference','Conference',''),('record','Record','Verified completed games, including non-D1 opponents; exhibitions excluded.'),('rating','Strength','Overall strength index: the average D1 team is 50.0, and ten points represent one standard deviation. Higher is stronger.'),('sd','SD','Standard deviations above or below the Division I mean. Positive is above average; negative is below average.'),('change','Change','Rank movement since the previous published Eastern date. Positive means moved up.'),('offense','Adj. Offense','Points scored per 100 possessions, adjusted for the opposing defense and site. Higher is stronger.'),('defense','Adj. Defense','Points allowed per 100 possessions, adjusted for the opposing offense and site. Lower is stronger.'),('sos','SOS Rank','Schedule difficulty based on opponents faced. #1 means toughest.'),('games','D1 Games','Completed, verified Division I games used by the model.'),('form','Recent Form','Recent opponent-adjusted team performance.'),('kenpom','Opening KP','KenPom preseason rank in the frozen opening snapshot.')]
 # Derive offense and defense box-score aggregates from independently verified finals.
 verified=json.loads((ROOT/f'data/cbb/strength-games/{data["season"]}.json').read_text())
 totals={}
 for g in verified.get('games',[]):
  if g.get('opponent_classification')!='d1' or len(g['teams'])!=2:continue
  ids=list(g['teams'])
  for tid in ids:
   b=g['teams'][tid];o=g['teams'][next(i for i in ids if i!=tid)]
   t=totals.setdefault(tid,{'gp':0})
   t['gp']+=1
   for key in ('points','fgm','fga','tpm','ftm','fta','oreb','tov'):
    t[key]=t.get(key,0)+b[key]
    t['opp_'+key]=t.get('opp_'+key,0)+o[key]
 def rate(tid,key,denom='gp',mult=1):
  t=totals.get(str(tid),{});return mult*t[key]/t[denom] if t.get(denom) else None
 variants={"offense":[["rank","Rank"],["logo",""],["name","Team"],["conference","Conference"],["record","Record"],["offrating","OFF Rating"],["ppg","PPG"],["offense","Adjusted OFF"],["fgpct","FG%"],["efgpct","eFG%"],["twopct","2P%"],["paint","Paint PPG"],["threerate","3P Rate"],["threepct","3P%"],["threepg","3PM/G"],["ftpct","FT%"],["ftattempt","FT Attempt Rate"],["assists","AST/G"],["tov","TOV/G"],["reb","REB/G"],["oreb","OFF Reb/G"],["rebshare","Total Rebound Rate"],["pace","Pace"],["games","D1 Games"]],"defense":[["rank","Rank"],["logo",""],["name","Team"],["conference","Conference"],["record","Record"],["defrating","DEF Rating"],["allowed","PPG Allowed"],["defense","Adjusted DEF"],["oppfgpct","OPP FG%"],["paintallowed","Paint PPG Allowed"],["oppthreerate","OPP 3P Rate"],["oppthreepg","OPP 3PM/G"],["steals","STL/G"],["blocks","BLK/G"],["forced","Forced TOV/G"],["margin","Turnover Margin"],["oppreb","REB Allowed/G"],["opporeb","OPP OFF Reb/G"],["games","D1 Games"]]}
 # Reuse the regular-season metrics displayed on the individual team pages.
 archives={}
 for t in data['teams']:
  p=ROOT/'data/cbb/teams'/(t['slug']+'.json')
  if p.exists():
   d=json.loads(p.read_text());archives[t['team_id']]=d.get('seasons',{}).get(str(data['season']),{}).get('phases',{}).get('regular',{}).get('metrics',{})
 def compute(tid):
  m=archives.get(str(tid),{});gp=m.get('gamesPlayed') or 0
  def ratio(n,d,scale=1):
   return scale*n/d if isinstance(n,(int,float)) and isinstance(d,(int,float)) and d>0 else None
  fgm=m.get('fieldGoalsMade');fga=m.get('fieldGoalsAttempted');thm=m.get('threePointFieldGoalsMade');tha=m.get('threePointFieldGoalsAttempted');ftm=m.get('freeThrowsMade');fta=m.get('freeThrowsAttempted');oreb=m.get('offensiveRebounds');tov=m.get('turnovers')
  pos=(fga-oreb+tov+.475*fta) if all(isinstance(v,(int,float)) for v in (fga,oreb,tov,fta)) else None
  reb=m.get('rebounds') or m.get('totalRebounds');diff=m.get('reboundsDifferential');oppreb=reb-diff if isinstance(reb,(int,float)) and isinstance(diff,(int,float)) else None
  return {'ppg':m.get('avgPoints'),'fgpct':m.get('fieldGoalPct'),'twopct':m.get('twoPointFieldGoalPct'),'threepct':m.get('threePointFieldGoalPct'),'threepg':ratio(thm,gp),'threerate':ratio(tha,fga,100),'efgpct':ratio(fgm+.5*thm if fgm is not None and thm is not None else None,fga,100),'ftpct':m.get('freeThrowPct'),'ftattempt':ratio(fta,fga,100),'oreb':ratio(oreb,gp),'reb':m.get('avgRebounds'),'rebshare':ratio(reb,reb+oppreb if oppreb is not None else None,100),'assists':m.get('avgAssists'),'tov':m.get('avgTurnovers'),'steals':m.get('avgSteals'),'blocks':m.get('avgBlocks'),'paint':m.get('avgPointsInPaint'),'offrating':ratio(m.get('points'),pos,100),'pace':ratio(pos,gp),'allowed':rate(tid,'opp_points'),'oppreb':ratio(oppreb,gp),'oppthreerate':ratio(m.get('opponentThreePointFieldGoalsAttempted'),m.get('opponentFieldGoalsAttempted'),100),'paintallowed':ratio(m.get('opponentPointsInPaint'),gp),'forced':ratio(m.get('opponentTurnovers'),gp),'margin':ratio(m.get('opponentTurnovers')-tov if m.get('opponentTurnovers') is not None and tov is not None else None,gp),'defrating':ratio(rate(tid,'opp_points')*gp if rate(tid,'opp_points') is not None else None,pos,100)}
 for mode,path,label in [('overall','cbb/rankings/index.html','Team Strength'),('offense','cbb/rankings/offense/index.html','Offensive Strength'),('defense','cbb/rankings/defense/index.html','Defensive Strength')]:
  eligible=data['teams'] if mode=='overall' else sorted([t for t in data['teams'] if t.get(mode+'_rank')],key=lambda t:t[mode+'_rank'])
  active_columns=columns if mode=='overall' else [(k,label,'') for k,label in variants[mode]]
  header=''
  for key,title,helptext in active_columns:
   btn=f'<button type="button" data-sort="{key}">{E(title)}<span class="sort-arrow" aria-hidden="true"></span></button>' if key not in ('logo','record') else E(title)
   helpbtn=f' <button type="button" class="help-btn" aria-label="Define {E(title)}" aria-expanded="false" data-help="{E(helptext)}">?</button>' if helptext else ''
   header+=f'<th scope="col">{btn}{helpbtn}</th>'
  rows=[]
  def fmt(v,digits=1):return '—' if v is None else f'{v:.{digits}f}'
  for t in eligible:
   rank=t['rank'] if mode=='overall' else t[mode+'_rank'];change=t['rank_change'] if mode=='overall' else None
   values={'rank':rank,'name':t['name'],'conference':conference_name(t['conference']), 'rating':t['strength_score'],'sd':(t['strength_score']-50)/10,'change':change,'offense':t['offensive_rating'],'defense':t['defensive_rating'],'sos':t.get('sos_rank'),'games':t['d1_games'],'form':t['recent_form'],'prior':100*t['preseason_weight'],'kenpom':t['source_ranks']['kenpom'],'torvik':t['source_ranks']['torvik']}
   values.update({'ppg':rate(t['team_id'],'points'),'fgpct':rate(t['team_id'],'fgm','fga',100),'threepg':rate(t['team_id'],'tpm'),'ftpct':rate(t['team_id'],'ftm','fta',100),'oreb':rate(t['team_id'],'oreb'),'tov':rate(t['team_id'],'tov'),'allowed':rate(t['team_id'],'opp_points'),'oppfgpct':rate(t['team_id'],'opp_fgm','opp_fga',100),'oppthreepg':rate(t['team_id'],'opp_tpm'),'opporeb':rate(t['team_id'],'opp_oreb'),'forced':rate(t['team_id'],'opp_tov')})
   values.update({k:v for k,v in compute(t['team_id']).items() if v is not None})
   attrs=' '.join(f'data-{k}="{E(v) if v is not None else ""}"' for k,v in values.items())
   teamurl='/cbb/teams/'+t['slug']+'/'
   cells=[str(rank),f'<a href="{teamurl}" aria-label="{E(t["name"])}"><img src="{E(t["logo"])}" alt="" width="26" height="26" loading="lazy"></a>',f'<a class="nba-rank-team" href="{teamurl}">{E(t["name"])}</a>',E(conference_name(t['conference'])),f'{t["wins"]}–{t["losses"]}',fmt(t['strength_score']),f'{(t["strength_score"]-50)/10:+.2f}',f'{change:+d}' if change else '—',fmt(t['offensive_rating']),fmt(t['defensive_rating']),str(t.get('sos_rank') or '—'),str(t['d1_games']),fmt(t['recent_form']),str(t['source_ranks']['kenpom'])]
   if mode!='overall':
    distinct={'rank':str(rank),'logo':cells[1],'name':cells[2],'conference':cells[3],'record':cells[4],'offense':fmt(t['offensive_rating']),'defense':fmt(t['defensive_rating']),'games':str(t['d1_games'])}
    distinct.update({k:fmt(values[k]) for k in ('ppg','fgpct','threepg','ftpct','oreb','tov','allowed','oppfgpct','oppthreepg','opporeb','forced')})
    distinct.update({k:fmt(values.get(k)) for k,_ in variants[mode] if k not in distinct})
    cells=[distinct[k] for k,_,_ in active_columns]
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
