#!/usr/bin/env python3
"""Read-only cross-team MLB player-stat probe for a known traded player."""
import json
from pathlib import Path
from probe_mlb_player_season_stats import probe

def compare(first,second,player_id,group="hitting"):
    if first["season"]!=second["season"] or first["team_id"]==second["team_id"]:
        raise ValueError("Expected different teams in the same season")
    matches=[]
    for stage in (first,second):
        rows=[r for r in stage["groups"][group]["records"] if r["player_id"]==player_id]
        if len(rows)!=1:raise ValueError("Player must have exactly one entry per team")
        row=rows[0]
        if row["team_id"]!=stage["team_id"] or row.get("attribution")!="explicit_team_split":
            raise ValueError("Ambiguous traded-player team attribution")
        matches.append(row)
    return {"status":"TRADED_PLAYER_TEAM_SPLITS_VERIFIED_NOT_PUBLISHED",
        "season":first["season"],"player_id":player_id,"group":group,
        "team_ids":[r["team_id"] for r in matches],
        "games_played":[r["stats"].get("gamesPlayed") for r in matches],"published":False}

def main():
    # Harrison Bader: Yankees and Reds in 2023.
    year=2023;player_id=664056
    first=probe(year,147)
    second=probe(year,113)
    result=compare(first,second,player_id)
    path=Path("mlb/data/traded-player-2023-bader-audit.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps(result))
if __name__=="__main__":main()
