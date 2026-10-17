#!/usr/bin/env python3
"""Read-only, one-season MLB historical result retrieval (no box-score fetches).

Stages schedules/final scores without publishing or implying player-stat coverage.
Use --year for one explicit historical season; artifacts expire in GitHub Actions.
"""
import argparse
import json
from pathlib import Path
from stage_mlb_daily_backfill import fetch

PHASES={"R":"regular","D":"division_series","L":"league_championship","W":"world_series","F":"wild_card"}

def stage_season(year, crosswalk, fetcher=fetch):
    if not 2015<=year<=2026:
        raise ValueError("Season must be 2015 through 2026")
    mapping=crosswalk.get("teams",{})
    if len(mapping)!=30:
        raise ValueError("Requires audited 30-team MLB crosswalk")
    payload=fetcher(f"/schedule?sportId=1&startDate={year}-01-01&endDate={year}-12-31&gameTypes=R,D,L,W,F")
    games={}
    skipped=0
    warnings=[]
    duplicate_identical=0
    for day in payload.get("dates",[]):
        for g in day.get("games",[]):
            if g.get("status",{}).get("abstractGameState")!="Final":
                skipped+=1
                continue
            gid=str(g["gamePk"])
            home=g["teams"]["home"]
            away=g["teams"]["away"]
            hid=str(home["team"]["id"])
            aid=str(away["team"]["id"])
            if hid not in mapping or aid not in mapping or hid==aid:
                raise ValueError("Unknown or identical team ID in "+gid)
            if "score" not in home or "score" not in away:
                warnings.append({"game_id":gid,"reason":"final_status_missing_score","date":g.get("officialDate") or g.get("gameDate","")[:10]})
                continue
            hscore=home["score"]
            ascore=away["score"]
            if type(hscore)!=int or type(ascore)!=int or min(hscore,ascore)<0:
                raise ValueError("Invalid final score in "+gid)
            phase=PHASES.get(g.get("gameType"))
            if phase is None:
                raise ValueError("Unsupported game type "+gid)
            date=g.get("officialDate") or g["gameDate"][:10]
            if not date.startswith(str(year)+"-"):
                raise ValueError("Date outside requested season "+gid)
            record={"game_id":gid,"date":date,"season":year,"phase":phase,
                "home":{"slug":mapping[hid]["slug"],"mlb_id":hid,"runs":hscore},
                "away":{"slug":mapping[aid]["slug"],"mlb_id":aid,"runs":ascore},
                "player_records":{},"player_data_coverage":"not_loaded",
                "source":"MLB Stats API","market":None}
            if gid in games:
                if games[gid]!=record:
                    raise ValueError("Conflicting duplicate game ID "+gid)
                duplicate_identical+=1
                continue
            games[gid]=record
    counts={x["slug"]:0 for x in mapping.values()}
    for rec in games.values():
        if rec["phase"]=="regular":
            counts[rec["home"]["slug"]]+=1
            counts[rec["away"]["slug"]]+=1
    expected_by_slug={slug:(58 if year==2020 and slug in ("detroit-tigers","st-louis-cardinals") else 60 if year==2020 else 161 if year==2021 and slug in ("atlanta-braves","colorado-rockies") else 161 if year==2024 and slug in ("houston-astros","cleveland-guardians") else 162) for slug in counts}
    expected=60 if year==2020 else 162
    coverage={"team_game_counts":dict(sorted(counts.items())),
        "teams_below_expected_slugs":sorted(slug for slug,n in counts.items() if n<expected_by_slug[slug]),
        "regular_games":sum(v["phase"]=="regular" for v in games.values()),
        "postseason_games":sum(v["phase"]!="regular" for v in games.values()),
        "teams_at_expected":sum(n==expected_by_slug[slug] for slug,n in counts.items()),
        "teams_below_expected":sum(n<expected_by_slug[slug] for slug,n in counts.items()),
        "teams_over_expected":sum(n>expected_by_slug[slug] for slug,n in counts.items()),
        "min_team_games":min(counts.values()),"max_team_games":max(counts.values()),
        "expected_games_per_team":expected,"not_final":skipped,"quarantined_scoreless_games":len(warnings),"identical_duplicates_ignored":duplicate_identical}
    return {"status":"HISTORICAL_STAGING_ONLY","season":year,"games":games,"coverage":coverage,"warnings":warnings}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",type=int,required=True)
    p.add_argument("--crosswalk",default="mlb/data/mlb-team-identity-audit.json")
    p.add_argument("--out",default=None)
    args=p.parse_args()
    crosswalk=json.loads(Path(args.crosswalk).read_text())
    result=stage_season(args.year,crosswalk)
    target=Path(args.out or f"mlb/data/historical-stage-{args.year}.json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"year":args.year,"coverage":result["coverage"],
       "published":False}))
if __name__=="__main__":
    main()
