#!/usr/bin/env python3
"""Generate the first historical day batch from TeamRankings' published matchup links.

Only links belonging to the selected historical date are retained; doubleheaders
with '-2' stay distinct for later manual game-ID reconciliation.
"""
import argparse,json,pathlib,re,urllib.parse
p=argparse.ArgumentParser()
p.add_argument("--pilot",default="data/mlb/teamrankings-pilot.json")
p.add_argument("--date",default="2018-05-28")
p.add_argument("--output",default="data/mlb/teamrankings-2018-day-urls.txt")
a=p.parse_args()
doc=json.loads(pathlib.Path(a.pilot).read_text())
urls=set()
for game in doc.get("matches",[]):
    for url in game.get("links",[]):
        u=urllib.parse.urlsplit(url)
        if u.hostname not in {"www.teamrankings.com","www2.teamrankings.com"}:continue
        m=re.fullmatch(r"/mlb/matchup/([a-z0-9-]+-"+re.escape(a.date)+r"(?:-2)?)",u.path.rstrip("/"))
        if m:
            urls.add("https://www.teamrankings.com"+m.group(0)+"/over-under-movement")
out=pathlib.Path(a.output)
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text("\n".join(sorted(urls))+"\n")
print("Unique historical matchup URLs:",len(urls))
if len(urls)<10:raise SystemExit("Too few source matchup links to proceed")
