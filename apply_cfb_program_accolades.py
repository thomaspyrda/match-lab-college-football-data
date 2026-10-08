"""Update program honors without recalculating archived season statistics."""
import json,re
from cfb_program_accolades import DATA,ROOT,render
from build_cfb_team_pages import slug

def update_page(content,team_id,data):
 section=render(team_id,data)
 if not section:raise ValueError(f'Missing accolades for {team_id}')
 content=re.sub(r'<section id="programAccolades".*?</section>\s*','',content,flags=re.S)
 anchor='<p class="archive-note">Sources: <a href="https://collegefootballdata.com/">'
 if anchor not in content:raise ValueError(f'Missing bottom-of-page source anchor: {team_id}')
 content=content.replace(anchor,section+'\n'+anchor,1)
 if 'href="#programAccolades"' not in content:content=content.replace('<a href="#schedule">Schedule</a>','<a href="#schedule">Schedule</a><a href="#programAccolades">Accolades</a>',1)
 content=re.sub(r'/cfb/team-page\.css\?v=[^"\s]+','/cfb/team-page.css?v=accolades-20261008',content)
 content=re.sub(r'site-navigation\.js\?v=[^"\s]+','site-navigation-v3.js',content)
 assert content.count('id="programAccolades"')==1
 assert content.index('id="programAccolades"')>content.index('id="schedule"')
 return content

def main():
 data=json.loads(DATA.read_text());teams=json.loads((ROOT/'data/cfb/team-registry.json').read_text())['teams']
 for t in teams:
  p=ROOT/'cfb/teams'/slug(t['name'])/'index.html'
  if not p.exists():raise ValueError(f'Missing team page: {p}')
  p.write_text(update_page(p.read_text(),t['id'],data))
 print('Updated program accolades on',len(teams),'existing team pages')
if __name__=='__main__':main()
