from pathlib import Path
pages=list(Path("nba/teams").glob("*/index.html"))
changed=0
for path in pages:
    before=path.read_text()
    after=before.replace("team-research.js?v=nba-season-ats-20261017", "team-research.js?v=nba-push-tiles-20261017")
    if after!=before:
        path.write_text(after)
        changed+=1
print(f"Updated shared script cache reference on {changed} NBA team pages")
if changed!=30: raise SystemExit(f"Expected all 30 NBA team pages, updated {changed}")
