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
def historical_coverage(archive,slugs):
    """Read-only per-season game coverage audit, counting each game once per team."""
    coverage={}
    for year in range(2015,2026):
        counts={slug:0 for slug in slugs}
        duplicate_team_games=0
        seen=set()
        for gid,game in archive.get("games",{}).items():
            if game.get("phase")!="regular" or int(game.get("season",-1))!=year:
                continue
            home=game.get("home",{}).get("slug")
            away=game.get("away",{}).get("slug")
            if home==away or home not in counts or away not in counts or str(gid) in seen:
                duplicate_team_games+=1
                continue
            seen.add(str(gid))
            counts[home]+=1
            counts[away]+=1
        # 2026 is not yet complete; final full-season threshold applies only after season end.
        expected=60 if year==2020 else 162
        coverage[str(year)]={"expected_games_per_team":expected,
            "min_team_games":min(counts.values()),"max_team_games":max(counts.values()),
            "teams_at_expected":sum(n==expected for n in counts.values()),
            "teams_below_expected":sum(n<expected for n in counts.values()),
            "teams_over_expected":sum(n>expected for n in counts.values()),
            "invalid_team_games":duplicate_team_games}
    return coverage

def main():
    p=argparse.ArgumentParser();p.add_argument("--archive",default="mlb/data/internal-backfill-archive-preview.json");p.add_argument("--out",default="mlb/data/team-page-dry-run-report.json");a=p.parse_args()
    archive=json.loads(Path(a.archive).read_text());pages=list(Path("mlb/teams").glob("*/index.html"))
    if len(pages)!=30:raise ValueError("Expected 30 MLB pages")
    results=[]
    for page in pages:
        html=page.read_text();new,result=transform(html,archive,page.parent.name)
        if '<script type="application/json" id="team-season-data">' not in new:raise ValueError("Lost page data")
        results.append(result)
    coverage=historical_coverage(archive,[page.parent.name for page in pages])
    complete=all(row["teams_at_expected"]==30 and row["teams_over_expected"]==0 for row in coverage.values())
    report={"publication_ready":complete,
        "coverage_gate":"PASS" if complete else "BLOCKED_INCOMPLETE_HISTORICAL_ARCHIVE",
        "historical_season_coverage":coverage,
        "status":"NO_PUBLICATION","teams":len(results),"regular_games_added":sum(x["added_regular_games"] for x in results)//2,
      "postseason_games_kept_separate":sum(x["postseason_games_not_merged"] for x in results)//2,"details":results}
    Path(a.out).write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k!="details"}))
if __name__=="__main__":main()
