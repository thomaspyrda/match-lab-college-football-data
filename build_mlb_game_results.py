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

def recover_missing_final_scores(document):
    """Use MLB's individual official game feed where the season schedule lacks final scores."""
    attempted = recovered = 0
    seen_ids = set()
    for day in document.get("dates", []):
        for game in day.get("games", []):
            if game.get("gameType") != "R" or game.get("status", {}).get("abstractGameState") != "Final":
                continue
            home = game.get("teams", {}).get("home", {})
            away = game.get("teams", {}).get("away", {})
            if isinstance(home.get("score"), int) and isinstance(away.get("score"), int):
                continue
            gid = game.get("gamePk")
            if not isinstance(gid, int) or gid in seen_ids:
                continue
            seen_ids.add(gid)
            attempted += 1
            try:
                request = urllib.request.Request(
                    f"https://statsapi.mlb.com/api/v1.1/game/{gid}/feed/live",
                    headers={"User-Agent": "BetWiseResearch/1.0"})
                with urllib.request.urlopen(request, timeout=12) as response:
                    feed = json.load(response)
                if feed.get("gameData", {}).get("status", {}).get("abstractGameState") != "Final":
                    continue
                linescore = feed.get("liveData", {}).get("linescore", {}).get("teams", {})
                hs = linescore.get("home", {}).get("runs")
                ac = linescore.get("away", {}).get("runs")
                if isinstance(hs, int) and isinstance(ac, int):
                    home["score"], away["score"] = hs, ac
                    recovered += 1
            except (OSError, ValueError, KeyError):
                continue
    return attempted, recovered

def build(year, document):
    teams = defaultdict(list)
    seen = set()
    visited = set()
    quarantined = []
    status_games = defaultdict(list)
    # Preserve original status details so gaps can be investigated by game ID.
    for day in document.get("dates", []):
        for game in day.get("games", []):
            if game.get("gameType") != "R":
                continue
            state = game.get("status", {}).get("abstractGameState")
            detailed = game.get("status", {}).get("detailedState") or state or "Unknown"
            if state != "Final":
                home, away = game.get("teams",{}).get("home",{}),game.get("teams",{}).get("away",{})
                hid,aid=home.get("team",{}).get("id"),away.get("team",{}).get("id")
                if hid in IDS and aid in IDS:
                    label = "Cancelled" if "cancel" in detailed.lower() else "Postponed" if "postpon" in detailed.lower() else "Suspended" if "suspend" in detailed.lower() else "Scheduled"
                    for tid,oid,site in ((hid,aid,"Home"),(aid,hid,"Away")):
                        status_games[IDS[tid]].append({"game_id":game.get("gamePk"),"date":game.get("officialDate") or str(game.get("gameDate",""))[:10],"opponent":IDS[oid],"location":site,"result":label,"score":"—","status":label})
                continue
            gid = game.get("gamePk")
            if gid in visited:
                continue
            visited.add(gid)
            home, away = game["teams"]["home"], game["teams"]["away"]
            hid, aid = home["team"]["id"], away["team"]["id"]
            if hid not in IDS or aid not in IDS:
                continue
            hs, ac = home.get("score"), away.get("score")
            if not isinstance(hs, int) or not isinstance(ac, int):
                quarantined.append({"game_id":gid,"year":year,"reason":"final_without_score","date":game.get("officialDate"),"home_id":hid,"away_id":aid,"detailed_state":game.get("status",{}).get("detailedState")})
                for tid,oid,site in ((hid,aid,"Home"),(aid,hid,"Away")):
                    status_games[IDS[tid]].append({"game_id":gid,"date":game.get("officialDate") or str(game.get("gameDate",""))[:10],"opponent":IDS[oid],"location":site,"result":"Final — score unavailable","score":"—","status":"Final — score unavailable"})
                continue
            date = game.get("officialDate") or game["gameDate"][:10]
            if hs == ac:
                for tid,oid,site in ((hid,aid,"Home"),(aid,hid,"Away")):
                    status_games[IDS[tid]].append({"game_id":gid,"date":date,"opponent":IDS[oid],"location":site,"result":"T","score":f"{hs}-{ac}","status":"Tie"})
                continue
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
               "quarantined":quarantined,"teams":{}}
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
        # A postponed/suspended entry may also appear again as a completed game.
        # Prefer the completed record and retain only one status row per game ID.
        used={str(g["game_id"]) for g in games}
        extra=[]
        for row in status_games[slug]:
            key=str(row.get("game_id"))
            if key in used:
                continue
            used.add(key)
            extra.append(row)
        # Status-only events never contribute to betting records or W-L.
        payload["teams"][slug] = {"games":sorted(games+extra,key=lambda g:(g["date"],str(g["game_id"]))),"record":counts}
    assert sum(x["record"]["wins"]+x["record"]["losses"] for x in payload["teams"].values())==2*len(seen)
    return payload

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--years",nargs="+",type=int,required=True)
    args=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for year in args.years:
        if not 2015 <= year <= 2026:
            raise ValueError("Unsupported year")
        document=fetch(year)
        attempted,recovered=recover_missing_final_scores(document)
        print(year,"individual-game feeds checked",attempted,"scores recovered",recovered,flush=True)
        data=build(year,document)
        (OUT/f"{year}.json").write_text(json.dumps(data,separators=(",",":"),ensure_ascii=False)+"\n")
        print(year,sum(len(t["games"]) for t in data["teams"].values())//2,"games",len(data["quarantined"]),"quarantined")

if __name__=="__main__":
    main()
