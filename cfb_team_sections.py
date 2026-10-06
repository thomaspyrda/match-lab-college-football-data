"""NFL-style section rendering for source-backed CFB season details."""
import html
from datetime import datetime, timezone
from refresh_cfb_team_details import canon
def esc(v):return html.escape(str(v if v is not None else '—'),quote=True)
def fmt(v,pct=False):
 if v is None:return '—'
 return f'{v*100:.1f}%' if pct else f'{v:,.0f}' if float(v).is_integer() else f'{v:,.2f}'
def cls(v):return 'result-w' if v in ('W','O') else 'result-l' if v in ('L','U') else 'result-p'

def rank_metrics(details):
 for team,d in details.items():
  for pair in d.get('metrics',[]):
   for side in ['offense','defense']:
    value=pair.get(side)
    if value is None:continue
    label=pair['label'];higher=side=='offense'
    if label in ['Havoc rate','Stuff rate','Turnovers / turnovers forced']:higher=not higher
    pool=[p[side] for other in details.values() for p in other.get('metrics',[]) if p['label']==label and p.get(side) is not None]
    pair[side+'_rank']=1+sum(v>value if higher else v<value for v in pool)
    pair[side+'_field_size']=len(pool)

def season_result(season,postseason,full_record,current):
 year=season['year'];coaches=season.get('details',{}).get('coaches',[])
 final_ap=next((c['final_ap_rank'] for c in coaches if c.get('final_ap_rank')),None)
 if year==current:label='Season in progress'
 elif postseason:
  last=postseason[-1];note=last.get('notes') or 'Postseason'
  label=f"{note} · {last['result']} {last['points']:g}–{last['allowed']:g} vs {last['opponent']}"
  if 'national championship' in note.lower() and last['result']=='W':label='National champions · '+label
 else:label='Regular season completed · no postseason result in source'
 record=f"{full_record['wins']}-{full_record['losses']}"+(f"-{full_record['ties']}" if full_record['ties'] else '')
 return f'<article class="playoff-result-card"><span>SEASON RESULT</span><strong>{esc(label)}</strong></article><p class="archive-note">Overall record including postseason: {record}{" · Final AP #"+str(final_ap) if final_ap and year<current else ""}. Regular-season snapshot excludes bowls and playoffs.</p>'

FIELDS={
 'passing':[('completions','CMP'),('attempts','ATT'),('passing_yards','Yards'),('passing_tds','TD'),('interceptions','INT'),('completion_pct','CMP%'),('passer_rating','NCAA rating')],
 'rushing':[('carries','Carries'),('rushing_yards','Yards'),('rushing_tds','TD'),('yards_per_carry','Yards/carry')],
 'receiving':[('receptions','REC'),('receiving_yards','Yards'),('receiving_tds','TD'),('yards_per_reception','Yards/REC')],
 'tackles':[('combined_tackles','Total'),('solo_tackles','Solo'),('assists','Assists'),('tfl','TFL'),('sacks','Sacks')],
 'sacks':[('sacks','Sacks'),('tfl','TFL'),('qb_hits','QB hurries'),('combined_tackles','Tackles')],
 'interceptions':[('def_interceptions','INT'),('passes_defended','Passes defended'),('defensive_tds','Defensive TDs'),('interception_yards','Return yards'),('combined_tackles','Tackles')]
}
def sections(s):
 d=s.get('details') or {};coaches=d.get('coaches') or []
 coaching=''.join(f'<article class="coach-card"><small>HEAD COACH</small><b>{esc(c["name"])}</b><span>'+ (f'{esc(c.get("wins"))}–{esc(c.get("losses"))} · {esc(c.get("games"))} games credited' if c.get('games') else 'Season head coach · coaching record not supplied')+'</span></article>' for c in coaches)
 coaching=coaching or '<p class="archive-note">No head-coaching record returned by the source for this season.</p>'
 coaching+='<p class="archive-note">Head-coaching records: CollegeFootballData. Coordinator history is not supplied by this source. Multiple coaches are shown when credited with games.</p>'
 recruiting=d.get('recruiting')
 recruitment=(f'<div class="snapshot-grid"><article class="snapshot-card"><b>#{esc(recruiting["rank"])}</b><span>National recruiting class rank</span></article><article class="snapshot-card"><b>{fmt(recruiting.get("points"))}</b><span>Recruiting class points</span></article></div>' if recruiting and recruiting.get('rank') else '<p class="archive-note">Recruiting class ranking unavailable from the source.</p>')
 recruitment+=f'<p class="archive-note">{s["year"]} signing class · CollegeFootballData team recruiting rankings. This is the incoming recruiting class, not a roster or transfer-portal ranking.</p>'
 metrics=[]
 for pair in d.get('metrics',[]):
  cards=[]
  for side in ['offense','defense']:
   v=pair.get(side);rank=pair.get(side+'_rank')
   ranktext=f"FBS #{rank} of {pair[side+'_field_size']}" if rank else 'Source value unavailable'
   label=pair['label']
   if label=='Havoc rate' and side=='offense':label='Havoc allowed'
   if label=='Turnovers / turnovers forced':label='Turnovers' if side=='offense' else 'Turnovers forced'
   cards.append(f'<article class="metric-box metric-box--{side}"><span>{esc(label)}</span><strong>{fmt(v,pair.get("percent",False))}</strong><small>{ranktext}</small></article>')
  metrics.append('<div class="metric-pair">'+''.join(cards)+'</div>')
 metrics=''.join(metrics) or '<p class="archive-note">Season metrics unavailable from the source.</p>'
 metrics+='<p class="archive-note">CFBD season statistics, including postseason where supplied. Advanced metrics exclude garbage time. PPA is predicted points added per play. Explosiveness is the provider’s successful-play metric, not an explosive-play percentage. FBS ranks compare the same source metric and season; ties share ranks.</p>'
 leaders=[]
 for category,fields in FIELDS.items():
  p=(d.get('leaders') or {}).get(category);title='Defensive Interceptions' if category=='interceptions' else category.title()
  if p:
   stats=p['stats'];content=f'<div class="season-leader-person"><div class="season-leader-identity"><div><h3>{esc(p["name"])}</h3></div></div><p class="season-leader-rank">FBS #{p["rank"]} · {fmt(p["league_total"])} season total</p><div class="season-leader-stats">'+''.join(f'<span><b>{fmt(stats.get(k))+("%" if k=="completion_pct" and stats.get(k) is not None else "")}</b><small>{esc(label)}</small></span>' for k,label in fields)+'</div>'+ (f'<p class="archive-note"><a href="{esc(p["source_url"])}">ESPN season statistics</a></p>' if p.get('source_url') else '')+'</div>'
  else:content='<p class="season-leader-empty">No positive total returned for this category.</p>'
  leaders.append(f'<article class="season-leader-card"><p class="season-leader-category">{title} Leader</p>{content}</article>')
 playerhtml='<div class="season-leader-grid">'+''.join(leaders)+'</div><p class="season-leader-note">Full-season player totals include bowls and playoffs. Each category starts with its main metric and uses secondary statistics only to break team ties. FBS ranks use combined player totals across FBS teams; tied totals share ranks. Defensive TDs follow the provider’s defensive-return touchdown totals. A dash means the provider did not return that statistic. CFBD is the primary source; 2015 defensive statistics are supplemented from ESPN.</p>'
 return {'coachingGrid':coaching,'recruitingContent':recruitment,'metricsGrid':metrics,'seasonLeadersContent':playerhtml,'seasonResult':s.get('season_result_html','')}

def attach_details(seasons,details_file,registry,build_season,current):
 from build_cfb_team_pages import slug,BASE
 counts={}
 for g in details_file['games']:
  if g.get('result'):
   for side in ['home','away']:
    team=canon(g[side]);counts[team]=counts.get(team,0)+1
 for team,d in details_file['teams'].items():
  for pair in d.get('metrics',[]):
   if pair['label'] in ['Total yards','Passing yards','Rushing yards'] and counts.get(team):
    pair['label']+=' per game'
    for side in ['offense','defense']:
     if pair.get(side) is not None:pair[side]/=counts[team]
 rank_metrics(details_file['teams'])
 games=details_file['games'];regular=[g for g in games if g['season_type']=='regular'];allseasons=build_season(games,details_file['year'])
 rebuilt=build_season(regular,details_file['year'])
 for tid,s in rebuilt.items():
  if tid not in registry:continue
  s['details']=details_file['teams'].get(canon(s['name']),{})
  s['details_updated_at']=details_file['updated_at'];s['details_sources']=details_file['sources']
  full=allseasons.get(tid,s);schedule=[]
  for g in games:
   side='home' if str(g.get('home_id'))==tid else 'away' if str(g.get('away_id'))==tid else None
   if not side or not g.get('start_date'):continue
   other='away' if side=='home' else 'home';r=g.get('result') or {};pf=r.get(side+'_points');pa=r.get(other+'_points');spread=g.get('spread')
   spread=spread if side=='home' or spread is None else -spread;total=g.get('over_under');done=pf is not None and pa is not None
   row={'id':g['game_id'],'week':g['week'],'date':g['start_date'],'season_type':g['season_type'],'notes':g.get('notes'),
    'site':'N' if g.get('neutral_site') else 'H' if side=='home' else 'A','opponent':g[other],'opponent_id':str(g[other+'_id']),
    'result':('W' if pf>pa else 'L' if pf<pa else 'T') if done else None,'points':pf,'allowed':pa,'spread':spread,'total':total,
    'ats':('W' if pf+spread>pa else 'L' if pf+spread<pa else 'P') if done and spread is not None else None,
    'ou':('O' if pf+pa>total else 'U' if pf+pa<total else 'P') if done and total is not None else None}
   opp=registry.get(row['opponent_id'])
   if opp:row['opponent_url']=BASE+f'/cfb/teams/{slug(opp["name"])}/'
   schedule.append(row)
  s['schedule']=sorted(schedule,key=lambda g:(g['date'],g['id']))
  post=[g for g in s['schedule'] if g['season_type']=='postseason' and g['result']]
  s['season_result_html']=season_result(s,post,full['record'],current)
  s['sections']=sections(s)
  seasons[tid]=s
 return seasons
