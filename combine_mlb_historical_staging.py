#!/usr/bin/env python3
"""Combine audited MLB historical season artifacts without touching live pages."""
import argparse
import json
from pathlib import Path

def combine(seasons, reconciliations):
    games={}
    years=set()
    for stage in seasons:
        year=int(stage["season"])
        if year in years:
            raise ValueError(f"Repeated season: {year}")
        years.add(year)
        if stage.get("status")!="HISTORICAL_STAGING_ONLY":
            raise ValueError(f"Untrusted stage: {year}")
        audit=reconciliations.get(year)
        if not audit or audit.get("year")!=year or audit.get("teams_checked")!=30 or audit.get("teams_matching")!=30 or audit.get("teams_mismatching"):
            raise ValueError(f"Official W/L reconciliation missing or failed: {year}")
        for gid,game in stage.get("games",{}).items():
            if str(game.get("game_id"))!=str(gid) or game.get("season")!=year:
                raise ValueError(f"Inconsistent ID or season: {gid}")
            if gid in games:
                if games[gid]!=game:
                    raise ValueError(f"Conflicting game across seasons: {gid}")
                raise ValueError(f"Repeated game ID: {gid}")
            games[gid]=game
    return {"schema_version":1,"status":"VERIFIED_STAGING_NO_PUBLICATION",
        "years":sorted(years),"games":games,"total_games":len(games)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--directory",default="mlb/data")
    p.add_argument("--out",default="mlb/data/historical-combined-preview.json")
    args=p.parse_args()
    root=Path(args.directory)
    stages=[]
    audits={}
    for file in sorted(root.glob("historical-stage-????.json")):
        stage=json.loads(file.read_text())
        year=int(stage["season"])
        audit_file=root/f"historical-reconciliation-{year}.json"
        if not audit_file.exists():
            raise ValueError(f"Missing reconciliation: {year}")
        stages.append(stage)
        audits[year]=json.loads(audit_file.read_text())
    if not stages:raise ValueError("No historical season artifacts provided")
    result=combine(stages,audits)
    dest=Path(args.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"years":result["years"],
                      "games":result["total_games"],"published":False}))
if __name__=="__main__":main()
