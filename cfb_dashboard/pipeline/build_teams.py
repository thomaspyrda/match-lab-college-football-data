"""Publish the current FBS conference directory alongside the matchup dashboard."""
import html
import json
import re
from pathlib import Path
from cfb_dashboard.pipeline.build_dashboard import canon

ROOT=Path(__file__).resolve().parents[2]
def esc(value):return html.escape(str(value),quote=True)
def slug(value):return re.sub(r'[^a-z0-9]+','-',value.lower()).strip('-')

def main():
 metadata=json.loads((ROOT/'data/cfb_dashboard_team_metadata.json').read_text())['teams']
 rankings=json.loads((ROOT/'data/current_rankings.json').read_text())
 board={canon(row['team']):row for row in rankings['teams']}
 history=json.loads((ROOT/'data/historical'/f"{rankings['season']}.json").read_text())
 conferences={}
 for game in sorted(history['games'],key=lambda row:row.get('week',0)):
  for side in ('home','away'):
   conferences[canon(game[side])]=game.get(side+'_conference') or 'FBS Independents'
 groups={}
 for name,meta in metadata.items():
  conference=meta.get('conference') or conferences.get(canon(name)) or 'FBS Independents'
  groups.setdefault(conference,[]).append((name,meta,board.get(canon(name),{})))
 parts=[]
 for conference,teams in sorted(groups.items()):
  cards=[]
  for name,meta,row in sorted(teams):
   details=[]
   if row.get('record'):details.append(row['record'])
   if row.get('national_strength_rank'):details.append(f"Team Strength #{row['national_strength_rank']}")
   logo=meta.get('logo') or f"https://a.espncdn.com/i/teamlogos/ncaa/500/{meta['espn_id']}.png"
   cards.append(f'<article class="conference-team"><img src="{esc(logo)}" alt="{esc(name)} logo" loading="lazy" width="48" height="48"><div><strong>{esc(name)}</strong><small>{esc(" · ".join(details) or conference)}</small></div></article>')
  parts.append(f'<section class="conference-group" id="{slug(conference)}"><h2>{esc(conference)} <small>({len(teams)})</small></h2><div class="conference-teams">'+''.join(cards)+'</div></section>')
 jumps=''.join(f'<a href="#{slug(conf)}">{esc(conf)}</a>' for conf in sorted(groups))
 template=(ROOT/'cfb_dashboard/teams-template.html').read_text()
 page=template.replace('__TEAM_COUNT__',str(len(metadata))).replace('__CONFERENCE_JUMPS__',jumps).replace('__CONFERENCE_GROUPS__',''.join(parts))
 (ROOT/'teams.html').write_text(page)
 print(f"Built {len(metadata)} CFB teams across {len(groups)} conferences")
if __name__=='__main__':main()
