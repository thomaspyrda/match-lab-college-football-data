#!/usr/bin/env python3
"""Dry-run MLB page Schedule & Results update, preserving all other HTML.

Uses only staged regular-season games in regular season slots. Postseason games
remain in their own audit section and never alter regular-season W-L records.
No page files are written by this tool.
"""
import argparse,json,re
from pathlib import Path
from html import unescape
from preview_mlb_team_page_backfill import prepare

PATTERN=re.compile(r'(<script type="application/json" id="team-season-data">)(.*?)(</script>)',re.S)
def transform(html,archive,slug):
    info=prepare(archive,html,slug);m=PATTERN.search(html)
    if not m:raise ValueError("Missing team data")
    current=json.loads(unescape(m.group(2))); changed=0
    season_by_key={str(s["key"]):s for s in current.get("seasons",[])}
    for year,buckets in info["backfill_seasons"].items():
        if not buckets["regular"]:continue
        if year not in season_by_key:raise ValueError("Missing MLB regular-season slot "+year)
        season=season_by_key[year]
        original={str(g.get("game_id")):g for g in season.get("games",[]) if g.get("game_id") is not None}
        for row in buckets["regular"]:
            gid=str(row["game_id"])
            if gid in original:
                g=original[gid]
                expected={
                    "date":row["date"],
                    "result":row["result"],
                    "score":str(row["score_for"])+"–"+str(row["score_against"]),
                    "location":row["location"],
                    "opponent":row["opponent_slug"].replace("-"," ").title()
                }
                for field,value in expected.items():
                    if g.get(field) is not None and str(g[field]).strip()!=str(value):
                        # Allow either standard score separator when comparing scores.
                        if field=="score" and str(g[field]).replace("-","–").strip()==str(value):
                            continue
                        raise ValueError("Conflict: "+gid+" "+field)
                continue
            original[gid]={"game_id":gid,"date":row["date"],"opponent":row["opponent_slug"].replace("-"," ").title(),
                "result":row["result"],"score":str(row["score_for"])+"–"+str(row["score_against"]),
                "location":row["location"],"source":row["source"]}
            changed+=1
        season["games"]=sorted(original.values(),key=lambda g:(g["date"],str(g.get("game_id",""))))
        season["game_data_coverage"]="partial_verified_game_results"
    output=PATTERN.sub(lambda _:m.group(1)+json.dumps(current,ensure_ascii=False,separators=(",",":")).replace("<","\\u003c")+m.group(3),html,count=1)
    return output,{"slug":slug,"added_regular_games":changed,"postseason_games_not_merged":sum(len(v["postseason"]) for v in info["backfill_seasons"].values())}
def main():
    p=argparse.ArgumentParser();p.add_argument("--archive",default="mlb/data/internal-backfill-archive-preview.json");p.add_argument("--out",default="mlb/data/team-page-dry-run-report.json");a=p.parse_args()
    archive=json.loads(Path(a.archive).read_text());pages=list(Path("mlb/teams").glob("*/index.html"))
    if len(pages)!=30:raise ValueError("Expected 30 MLB pages")
    results=[]
    for page in pages:
        html=page.read_text();new,result=transform(html,archive,page.parent.name)
        if '<script type="application/json" id="team-season-data">' not in new:raise ValueError("Lost page data")
        results.append(result)
    report={"status":"NO_PUBLICATION","teams":len(results),"regular_games_added":sum(x["added_regular_games"] for x in results)//2,
      "postseason_games_kept_separate":sum(x["postseason_games_not_merged"] for x in results)//2,"details":results}
    Path(a.out).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="details"}))
if __name__=="__main__":main()
