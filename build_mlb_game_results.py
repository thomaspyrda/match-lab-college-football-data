#!/usr/bin/env python3
"""Build official MLB game results and explicitly standardized market comparisons."""
import argparse
import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from build_mlb_season_snapshots import IDS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data/mlb/game-results"

def fetch(year):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={year}&gameType=R"
    req = urllib.request.Request(url, headers={"User-Agent":"BetWiseResearch/1.0"})
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)

def build(year, document):
    teams = defaultdict(list)
    seen = set()
    for day in document.get("dates", []):
        for game in day.get("games", []):
            if game.get("gameType") != "R" or game.get("status", {}).get("abstractGameState") != "Final":
                continue
            gid = game.get("gamePk")
            if gid in seen:
                continue
            home, away = game["teams"]["home"], game["teams"]["away"]
            hid, aid = home["team"]["id"], away["team"]["id"]
            if hid not in IDS or aid not in IDS:
                continue
            hs, ac = home.get("score"), away.get("score")
            if not isinstance(hs, int) or not isinstance(ac, int):
                raise ValueError(f"Missing final score: {gid}")
            date = game.get("officialDate") or game["gameDate"][:10]
            if hs == ac:
                raise ValueError(f"Tied final game requires manual review: {gid}")
            seen.add(gid)
            for teamid, opponentid, home_side, scored, conceded in ((hid,aid,True,hs,ac),(aid,hid,False,ac,hs)):
                margin = scored - conceded
                total = scored + conceded
                # Standardized +1.5 for the team; this is not a closing sportsbook line.
                ats = "W" if margin >= -1 else "L"
                ou = "O" if total > 8.5 else "U"
                teams[IDS[teamid]].append({
                    "game_id":gid,"date":date,"opponent":IDS[opponentid],
                    "location":"Home" if home_side else "Away",
                    "result":"W" if margin > 0 else "L",
                    "score":f"{scored}-{conceded}",
                    "runs_for":scored,"runs_against":conceded,
                    "runline_plus_1_5":ats,"total_8_5":ou,
                })
    payload = {"season":year,"source":"MLB Stats API official regular-season finals",
               "market_method":"standardized_not_sportsbook",
               "runline_assumption":"Each team +1.5 runs; not reciprocal game-specific sportsbook odds",
               "total_assumption":8.5,
               "teams":{}}
    for slug in IDS.values():
        games = sorted(teams[slug], key=lambda g:(g["date"],g["game_id"]))
        counts = {"wins":sum(g["result"]=="W" for g in games),
                  "losses":sum(g["result"]=="L" for g in games),
                  "runline_wins":sum(g["runline_plus_1_5"]=="W" for g in games),
                  "runline_losses":sum(g["runline_plus_1_5"]=="L" for g in games),
                  "overs":sum(g["total_8_5"]=="O" for g in games),
                  "unders":sum(g["total_8_5"]=="U" for g in games)}
        assert counts["wins"]+counts["losses"]==len(games)
        assert counts["overs"]+counts["unders"]==len(games)
        assert counts["runline_wins"]+counts["runline_losses"]==len(games)
        payload["teams"][slug] = {"games":games,"record":counts}
    assert sum(len(x["games"]) for x in payload["teams"].values())==2*len(seen)
    return payload

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--years",nargs="+",type=int,required=True)
    args=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for year in args.years:
        if not 2015 <= year <= 2026:
            raise ValueError("Unsupported year")
        data=build(year,fetch(year))
        (OUT/f"{year}.json").write_text(json.dumps(data,separators=(",",":"),ensure_ascii=False)+"\n")
        print(year,sum(len(t["games"]) for t in data["teams"].values())//2,"games")

if __name__=="__main__":
    main()
