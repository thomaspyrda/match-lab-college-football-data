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
# Canonical NFL franchise routes, including historical draft abbreviations.
NFL_TEAM_SLUGS={
 "ARI":"arizona-cardinals",
 "ATL":"atlanta-falcons",
 "BAL":"baltimore-ravens",
 "BUF":"buffalo-bills",
 "CAR":"carolina-panthers",
 "CHI":"chicago-bears",
 "CIN":"cincinnati-bengals",
 "CLE":"cleveland-browns",
 "DAL":"dallas-cowboys",
 "DEN":"denver-broncos",
 "DET":"detroit-lions",
 "GB":"green-bay-packers",
 "HOU":"houston-texans",
 "IND":"indianapolis-colts",
 "JAX":"jacksonville-jaguars",
 "KC":"kansas-city-chiefs",
 "LAC":"los-angeles-chargers",
 "LA":"los-angeles-rams",
 "LV":"las-vegas-raiders",
 "MIA":"miami-dolphins",
 "MIN":"minnesota-vikings",
 "NE":"new-england-patriots",
 "NO":"new-orleans-saints",
 "NYG":"new-york-giants",
 "NYJ":"new-york-jets",
 "OAK":"las-vegas-raiders",
 "PHI":"philadelphia-eagles",
 "PIT":"pittsburgh-steelers",
 "SEA":"seattle-seahawks",
 "SF":"san-francisco-49ers",
 "TB":"tampa-bay-buccaneers",
 "TEN":"tennessee-titans",
 "WAS":"washington-commanders",
 "BOS":"new-england-patriots",
 "GNB":"green-bay-packers",
 "KAN":"kansas-city-chiefs",
 "NOR":"new-orleans-saints",
 "NWE":"new-england-patriots",
 "PHO":"arizona-cardinals",
 "RAI":"las-vegas-raiders",
 "RAM":"los-angeles-rams",
 "SDG":"los-angeles-chargers",
 "SFO":"san-francisco-49ers",
 "STL":"los-angeles-rams",
 "TAM":"tampa-bay-buccaneers",
}
def nfl_team_link(abbr):
 code=str(abbr).strip().upper()
 slug=NFL_TEAM_SLUGS.get(code)
 if not slug:return esc(abbr)
 return f'<a href="https://nfl.parlaycalculator.bet/{slug}.html" title="{esc(code)} NFL team history">{esc(abbr)}</a>'

def render(team_id,data=None):
 if data is None:
  if not DATA.exists():return ''
  data=json.loads(DATA.read_text())
 t=data['teams'].get(str(team_id));sources=data['sources']
 if not t:return ''
 bowls=t['bowl_wins'];conference=t['conference_titles'];national=t['national_titles'];awards=t['player_awards'];draft=t.get('first_round_draft_picks',[])
 counts=[('Bowl Wins',sum(not r.get('vacated') for r in bowls)),('Conference Titles',sum(not r.get('vacated') for r in conference)),('National Titles',sum(r.get('claimed',False) for r in national)),('Major Player Awards',len(awards)),('NFL First-Round Picks',len(draft))]
 summary=''.join(f'<article class="snapshot-card"><b>{v}</b><span>{label}</span></article>' for label,v in counts)
 def details(title,headers,rows,note=''):
  return f'<details class="accolade-history"><summary>{title}<span aria-hidden="true">+</span></summary>'+table(headers,rows)+(f'<p class="archive-note">{note}</p>' if note else '')+'</details>'
 bowl_rows=[[str(r['year']),esc(r['bowl'])+(' (vacated)' if r.get('vacated') else ''),esc(r['opponent']),esc(r['score']),source_link(r,sources)] for r in bowls]
 conf_rows=[[str(r['year']),esc(r['conference']),('Shared' if r.get('shared') else 'Outright')+(' · vacated' if r.get('vacated') else ''),source_link(r,sources)] for r in conference]
 nat_rows=[[str(r['year'])+(' (not claimed)' if not r.get('claimed') else ''),esc(r['level']),esc(r['selectors'])+(f'<br><small>{esc(r["note"])}</small>' if r.get('note') else ''),source_link(r,sources)] for r in national]
 award_rows=[[str(r['year']),esc(r['award']),esc(r['player']),source_link(r,sources)] for r in awards]
 draft_rows=[[str(r['year']),esc(r['player']),esc(r['position']),f'#{r["overall_pick"]}',nfl_team_link(r['nfl_team']),source_link(r,sources)] for r in draft]
 return '<section id="programAccolades" class="team-section program-accolades"><div class="team-section-head"><p>PROGRAM ACCOLADES</p></div><p class="archive-note">Program history through '+str(data['coverage']['player_awards_through'])+'. These honors stay the same when you change the selected season.</p><div class="snapshot-grid accolade-summary">'+summary+'</div>'+details('Bowl Win History',['Season','Bowl','Opponent','Winning Score',''],bowl_rows,'Season years are used for January bowls. Playoff games played in named bowls count; standalone national championship games and campus playoff rounds do not. Vacated wins are excluded from the total.')+details('Conference Titles',['Season','Conference','Title',''],conf_rows,'Regular-season champions or championship-game winners, as listed in NCAA FBS/FCS records. Shared titles count once per program. Earlier titles outside these record books are not yet included.')+details('National Titles',['Season','Division','Selector / Recognition',''],nat_rows,'The total counts school-claimed FBS titles and NCAA FCS championships. Other NCAA major-selector selections are marked (not claimed) and excluded from that total. Titles in other divisions are not yet included.')+details('Major Player Awards',['Season','Award','Player',''],award_rows,'Includes the Heisman and major national performance, positional and scholar-athlete awards in the NCAA award book. Award wins count separately, including repeat winners and co-winners.')+details('NFL First-Round Draft Picks',['Draft Year','Player','Position','Overall Pick','NFL Team',''],draft_rows,f"NFL first-round draft selections cover {data['coverage'].get('nfl_first_round_draft_from','1970')}–{data['coverage'].get('nfl_first_round_draft_through','2026')}. Picks from 1970–2014 link to Pro-Football-Reference; picks from 2015–2026 link to the NFL team-page archive. Only current CFB team pages are included.")+'</section>'
