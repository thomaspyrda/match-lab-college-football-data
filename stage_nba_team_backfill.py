#!/usr/bin/env python3
"""Stage 2026-27 NBA regular-season team results from existing ESPN dashboard cache.

Dry-run by default. This script does not fetch external sources or edit live
NBA historical season files; it produces an auditable per-team import manifest.
"""
import argparse, json
from collections import Counter
from pathlib import Path
from nba_closing_markets import verified_closing_market
from daily_backfill_core import GameObservation, market_result, accept_pregame_market

ROOT=Path(__file__).resolve().parent
REGISTRY=ROOT/"data/sports/team-registry.json"
CACHE=ROOT/"nba/dashboard/data/completed-games.json"

def build_manifest(registry, cache, season=2027):
    lookup={str(t["espn_id"]):t for t in registry["teams"] if t.get("sport")=="nba"}
    if len(lookup)!=30:raise ValueError("Expected 30 NBA teams")
    grouped={t["slug"]:[] for t in lookup.values()}
    stats=Counter()
    for g in cache.get("games",[]):
        if g.get("season")!=season or g.get("phase")!=2:continue
        participants=g.get("teams") or {}
        if len(participants)!=2 or not all(str(i) in lookup for i in participants):raise ValueError("Unknown or incomplete NBA matchup "+str(g.get("id")))
        ids=list(participants);home=str(g["home"]);away=next(i for i in ids if str(i)!=home)
        home_score=int(participants[home]["points"]);away_score=int(participants[away]["points"])
        obs=GameObservation("nba",str(g["id"]),g["observed_complete_at"],g["date"][:10],home,away,"final",home_score,away_score);obs.validate()
        line=g.get("pregame_market") # Strictly saved pregame data; postgame pickcenter is not trusted as historical pregame.
        valid=bool(line and line.get("observed_at") and accept_pregame_market(g["date"],line["observed_at"],line))
        archived=verified_closing_market(g)
        if archived:
            line=archived;valid=True;stats['verified_closing_markets']+=1
        settlement=market_result("nba",home_score,away_score,home_spread=line.get("home_spread") if valid else None,total=line.get("total") if valid else None)
        for tid,other,venue,own_score,opp_score in ((home,away,"Home",home_score,away_score),(away,home,"Away",away_score,home_score)):
            home_ats=settlement["home_ats_or_runline"]
            ats=home_ats if tid==home else ({"W":"L","L":"W","P":"P"}.get(home_ats) if home_ats else None)
            grouped[lookup[tid]["slug"]].append({"game_id":g["id"],"date":g["date"][:10],"location":venue,"opponent_slug":lookup[other]["slug"],"opponent_name":lookup[other].get("name",lookup[other]["slug"]),"result":"W" if own_score>opp_score else "L","score_for":own_score,"score_against":opp_score,"spread":((line["home_spread"] if tid==home else -line["home_spread"]) if valid and line.get("home_spread") is not None else None),"total":line.get("total") if valid else None,"ats_result":ats,"ou_result":settlement["ou"],"players":g.get("players",{}).get(tid,[]),"odds_source":line.get("source") if valid else None,"odds_line_type":line.get("line_type","observed pregame") if valid else None,"odds_observed_at":line.get("observed_at") if valid else None})
        stats["games"]+=1
        if valid:stats["sourced_pregame_markets"]+=1
        else:stats["without_valid_pregame_market"]+=1
    for rows in grouped.values():rows.sort(key=lambda row:(row["date"],row["game_id"]))
    return {"season":season,"status":"STAGING_NOT_PUBLISHED","coverage":dict(stats),"teams":grouped}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--season",type=int,default=2027)
    parser.add_argument("--out",default="nba/dashboard/data/season-team-backfill-preview.json")
    args=parser.parse_args()
    registry=json.loads(REGISTRY.read_text());cache=json.loads(CACHE.read_text())
    manifest=build_manifest(registry,cache,args.season)
    path=ROOT/args.out;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps({"season":args.season,"teams":len(manifest["teams"]),"coverage":manifest["coverage"],"status":manifest["status"]}))
if __name__=="__main__":main()
