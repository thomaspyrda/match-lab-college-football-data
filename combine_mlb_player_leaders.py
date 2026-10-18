#!/usr/bin/env python3
"""Combine previously staged MLB player-leader artifacts; no API scraping or publication."""
import json,argparse
from pathlib import Path

YEARS=range(2015,2027)
def combine(root):
    teams={}
    totals={"hitters":0,"starters":0,"relievers":0}
    for year in YEARS:
        path=root/str(year)/"mlb"/"data"/f"mlb-player-leaders-{year}.json"
        obj=json.loads(path.read_text())
        if obj.get("season")!=year or obj.get("published") is not False:raise ValueError(f"{year}: invalid season or publication state")
        if len(obj["teams"])!=30:raise ValueError(f"{year}: expected 30 teams")
        for tid,entry in obj["teams"].items():
            if entry["season"]!=year or entry["team_id"]!=tid:raise ValueError(f"{year}/{tid}: identity mismatch")
            if entry.get("hitter_selection_basis")!="team_specific_season_at_bats_only":raise ValueError(f"{year}/{tid}: incorrect hitter ranking rule")
            h=entry["top_hitters"]; sp=entry["starting_pitchers"]; rp=entry["relief_pitchers"]
            if len(h)>20 or len(sp)>5 or len(rp)>5:raise ValueError(f"{year}/{tid}: selection limit exceeded")
            if [int(x["stats"]["atBats"]) for x in h]!=sorted((int(x["stats"]["atBats"]) for x in h),reverse=True):raise ValueError(f"{year}/{tid}: hitters out of at-bats order")
            if len({x["player_id"] for x in sp+rp})!=len(sp+rp):raise ValueError(f"{year}/{tid}: duplicate pitchers")
            for row in h+sp+rp:
                if row.get("team_id")!=tid or row.get("season")!=year or row.get("attribution")!="explicit_team_split":raise ValueError(f"{year}/{tid}: unverified team attribution")
            teams.setdefault(tid,{})[str(year)]={"hitters":h,"starters":sp,"relievers":rp}
            totals["hitters"]+=len(h);totals["starters"]+=len(sp);totals["relievers"]+=len(rp)
    return {"status":"MLB_HISTORICAL_LEADERS_REVIEW_ONLY","years":[2015,2026],"teams":teams,"totals":totals,"published":False,
            "note":"Selection ranks retrieved source records. Independent source-coverage audit remains required."}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",default="mlb/data/staged-artifacts");p.add_argument("--out",default="mlb/data/mlb-historical-player-leaders-review.json");a=p.parse_args()
    result=combine(Path(a.root));dest=Path(a.out);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"teams":len(result["teams"]),"totals":result["totals"],"published":False}))
