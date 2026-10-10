"""Attach the shared approved-layout shell to existing MLB/CBB team archives.
Idempotent: only adjusts asset tags, never removes roster, season, or team identities.
"""
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parent
TAG = 'data-archive-layout="mlb-cbb-v1"'
CSS = '<link rel="stylesheet" href="/sports-research/mlb-cbb-team-layout.css?v=20261010-college-v3" '+TAG+'>'
JS = '<script defer src="/sports-research/mlb-cbb-team-layout.js?v=20261010-college-v3" '+TAG+'></script>'
def main():
 for sport in ('mlb','cbb'):
  paths=list((ROOT / sport / 'teams').glob('*/index.html'))
  if not paths: raise RuntimeError(f"No {sport} team pages")
  changed=0
  for p in paths:
   text=p.read_text()
   if 'id="team-season-data"' not in text: raise RuntimeError(f"Missing season payload: {p}")
   text=re.sub(r'<link rel="stylesheet" href="/sports-research/mlb-cbb-team-layout\.css[^"]*" data-archive-layout="mlb-cbb-v1">','',text)
   text=re.sub(r'<script defer src="/sports-research/mlb-cbb-team-layout\.js[^"]*" data-archive-layout="mlb-cbb-v1"></script>','',text)
   if '</head>' not in text or '</body>' not in text: raise RuntimeError(f"Bad shell {p}")
   text=text.replace('</head>',CSS+'</head>',1).replace('</body>',JS+'</body>',1)
   p.write_text(text);changed+=1
  print(f"Updated {changed} {sport.upper()} team pages")
if __name__=='__main__':main()
