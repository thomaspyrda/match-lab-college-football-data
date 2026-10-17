#!/usr/bin/env python3
"""Preview MLB archived results in the existing team-page season-data format.

Read-only: writes a report, not HTML. Postseason results remain separate from
regular-season W-L totals. Existing page content must be preserved on publication.
"""
import argparse,json,re
from collections import defaultdict
from pathlib import Path
from html import unescape

ROOT=Path(__file__).resolve().parent
def prepare(archive, existing_html, slug):
    m=re.search(r'<script type="application/json" id="team-season-data">(.*?)</script>',existing_html,re.S)
    if not m:raise ValueError("Missing embedded team-season-data")
    seed=json.loads(unescape(m.group(1)))
    source=archive.get("games",{})
    years=defaultdict(lambda:{"regular":[],"postseason":[]})
    for gid,g in source.items():
        if str(g.get("game_id"))!=str(gid):raise ValueError("Inconsistent game ID")
        if slug not in (g["home"]["slug"],g["away"]["slug"]):continue
        home=g["home"]["slug"]==slug
        own=g["home"] if home else g["away"];opp=g["away"] if home else g["home"]
        row={"game_id":gid,"date":g["date"],"opponent_slug":opp["slug"],
             "location":"Home" if home else "Away","score_for":own["runs"],"score_against":opp["runs"],
             "result":"W" if own["runs"]>opp["runs"] else "L" if own["runs"]<opp["runs"] else "T",
             "source":g.get("source"),"game_type":g["phase"]}
        phase="regular" if g["phase"]=="regular" else "postseason"
        years[str(g["season"])][phase].append(row)
    for y in years.values():
        for kind in ("regular","postseason"):
            y[kind].sort(key=lambda r:(r["date"],r["game_id"]))
    return {"slug":slug,"team_id":seed["team_id"],"status":"PREVIEW_ONLY",
            "season_keys":[s["key"] for s in seed.get("seasons",[])],
            "backfill_seasons":dict(years)}
def main():
    p=argparse.ArgumentParser();p.add_argument("--archive",default="mlb/data/internal-backfill-archive-preview.json")
    p.add_argument("--out",default="mlb/data/team-page-adapter-preview.json");a=p.parse_args()
    archive=json.loads((ROOT/a.archive).read_text());registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())
    teams=[x for x in registry["teams"] if x.get("sport")=="mlb"]
    if len(teams)!=30:raise ValueError("Expected 30 teams")
    results={}
    for team in teams:
        slug=team["slug"];html=(ROOT/f"mlb/teams/{slug}/index.html").read_text()
        results[slug]=prepare(archive,html,slug)
    ids=[v["team_id"] for v in results.values()]
    if len(set(ids))!=30:raise ValueError("Duplicate page team ID")
    counts={"teams":len(results),"regular_games":sum(len(s["regular"]) for t in results.values() for s in t["backfill_seasons"].values())//2,
            "postseason_games":sum(len(s["postseason"]) for t in results.values() for s in t["backfill_seasons"].values())//2}
    report={"status":"PREVIEW_ONLY","coverage":counts,"teams":results}
    out=ROOT/a.out;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"coverage":counts}))
if __name__=="__main__":main()
