"""Attach CBB-only archive assets without replacing team pages or season seed data."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def main():
    registry=json.loads((ROOT/'data/sports/team-registry.json').read_text())
    count=0
    for team in registry['teams']:
        if team['sport']!='cbb':continue
        archive=ROOT/'data/cbb/teams'/f'{team["slug"]}.json'
        if not archive.exists():raise ValueError('Missing team archive '+team['slug'])
        data=json.loads(archive.read_text())
        if str(data['team_id'])!=str(team['espn_id']):raise ValueError('Team mismatch')
        page=ROOT/'cbb/teams'/team['slug']/'index.html'
        source=page.read_text()
        seed=re.search(r'<script[^>]*id="team-season-data"[^>]*>.*?</script>',source,re.S).group()
        source=re.sub(r'<script\b[^>]*data-archive-layout="mlb-cbb-v1"[^>]*>\s*</script>','',source)
        source=re.sub(r'<(?:script|link)\b[^>]*data-cbb-archive="v1"[^>]*>(?:\s*</script>)?','',source)
        source=source.replace('team-theme.js?v=2','team-theme.js?v=3')
        source=source.replace('</head>','<link rel="stylesheet" href="/sports-research/cbb-team-archive-v1.css?v=20261029-cbb-history-completion-v10" data-cbb-archive="v1"><script defer src="/sports-research/cbb-team-archive-v1.js?v=20261029-cbb-history-completion-v10" data-cbb-archive="v1"></script></head>')
        source=re.sub(r'site-navigation-v\d+\.js\?v=[\w-]+','site-navigation-v12.js?v=20261027-cbb-rankings',source)
        if any(s['phases']['regular']['completed_games'] for s in data['seasons'].values()):
            source=source.replace('content="noindex,follow"','content="index,follow"')
        assert seed in source,'Existing embedded history changed'
        page.write_text(source)
        count+=1
    print('Attached verified CBB archives to',count,'team pages; seed data preserved')
if __name__=='__main__':main()
