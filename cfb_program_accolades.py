"""Static program-wide honors, independent of the season selector."""
import html,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data/cfb/program-accolades.json'
def esc(v):return html.escape(str(v),quote=True)
def source_link(r,sources):
 s=sources[r['source']];url=s['url']+(f'#page={r["page"]}' if r.get('page') else '')
 return f'<a href="{esc(url)}">Source</a>'
def table(headers,rows):
 if not rows:return '<p class="archive-note">No entries recorded in the listed historical sources.</p>'
 return '<div class="schedule-wrap"><table class="team-schedule accolades-table"><thead><tr>'+''.join(f'<th>{esc(h)}</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join(f'<td>{v}</td>' for v in r)+'</tr>' for r in rows)+'</tbody></table></div>'
def render(team_id,data=None):
 if data is None:
  if not DATA.exists():return ''
  data=json.loads(DATA.read_text())
 t=data['teams'].get(str(team_id));sources=data['sources']
 if not t:return ''
 bowls=t['bowl_wins'];conference=t['conference_titles'];national=t['national_titles'];awards=t['player_awards']
 counts=[('Bowl Wins',sum(not r.get('vacated') for r in bowls)),('Conference Titles',sum(not r.get('vacated') for r in conference)),('National Titles',sum(r.get('claimed',False) for r in national)),('Major Player Awards',len(awards))]
 summary=''.join(f'<article class="snapshot-card"><b>{v}</b><span>{label}</span></article>' for label,v in counts)
 def details(title,headers,rows,note=''):
  return f'<details class="accolade-history"><summary>{title}<span aria-hidden="true">+</span></summary>'+table(headers,rows)+(f'<p class="archive-note">{note}</p>' if note else '')+'</details>'
 bowl_rows=[[str(r['year']),esc(r['bowl'])+(' (vacated)' if r.get('vacated') else ''),esc(r['opponent']),esc(r['score']),source_link(r,sources)] for r in bowls]
 conf_rows=[[str(r['year']),esc(r['conference']),('Shared' if r.get('shared') else 'Outright')+(' · vacated' if r.get('vacated') else ''),source_link(r,sources)] for r in conference]
 nat_rows=[[str(r['year'])+(' (not claimed)' if not r.get('claimed') else ''),esc(r['level']),esc(r['selectors'])+(f'<br><small>{esc(r["note"])}</small>' if r.get('note') else ''),source_link(r,sources)] for r in national]
 award_rows=[[str(r['year']),esc(r['award']),esc(r['player']),source_link(r,sources)] for r in awards]
 return '<section id="programAccolades" class="team-section program-accolades"><div class="team-section-head"><p>PROGRAM ACCOLADES</p></div><p class="archive-note">Program history through '+str(data['coverage']['player_awards_through'])+'. These honors stay the same when you change the selected season.</p><div class="snapshot-grid accolade-summary">'+summary+'</div>'+details('Bowl Win History',['Season','Bowl','Opponent','Winning Score',''],bowl_rows,'Season years are used for January bowls. Playoff games played in named bowls count; standalone national championship games and campus playoff rounds do not. Vacated wins are excluded from the total.')+details('Conference Titles',['Season','Conference','Title',''],conf_rows,'Regular-season champions or championship-game winners, as listed in NCAA FBS/FCS records. Shared titles count once per program. Earlier titles outside these record books are not yet included.')+details('National Titles',['Season','Division','Selector / Recognition',''],nat_rows,'The total counts school-claimed FBS titles and NCAA FCS championships. Other NCAA major-selector selections are marked (not claimed) and excluded from that total. Titles in other divisions are not yet included.')+details('Major Player Awards',['Season','Award','Player',''],award_rows,'Includes the Heisman and major national performance, positional and scholar-athlete awards in the NCAA award book. Award wins count separately, including repeat winners and co-winners.')+'</section>'
