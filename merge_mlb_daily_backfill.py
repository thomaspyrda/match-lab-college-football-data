#!/usr/bin/env python3
"""Merge staged MLB games into a separate, auditable archive (never live pages).

Checks both team identities, final scores, game type, idempotence and conflicts.
An archive is distinct from existing MLB team HTML and does not imply licensed
redistribution of MLB-sourced box scores.
"""
import argparse,json
from collections import Counter
from pathlib import Path

TYPES={"R":"regular","D":"division_series","L":"league_championship","W":"world_series","F":"wild_card"}
def merge_archive(previous, staged, team_crosswalk):
    if staged.get("status")!="STAGED_NOT_PUBLISHED":raise ValueError("Only audited staging accepted")
    mapping=team_crosswalk.get("teams",{})
    if len(mapping)!=30:raise ValueError("30-team crosswalk required")
    games=dict(previous.get("games",{}));metrics=Counter()
    for game_id,game in staged.get("games",{}).items():
        if str(game.get("game_id"))!=str(game_id):raise ValueError("Game ID mismatch")
        phase=TYPES.get(game.get("game_type"))
        if phase is None:raise ValueError("Unknown MLB phase for "+game_id)
        home=game.get("home",{});away=game.get("away",{})
        hi=str(home.get("id"));ai=str(away.get("id"))
        if hi==ai or hi not in mapping or ai not in mapping:raise ValueError("Unmatched MLB teams")
        if any(type(side.get("runs")) is not int or side["runs"]<0 for side in (home,away)):
            raise ValueError("Invalid MLB final score")
        players=game.get("players",{})
        if not players.get("home") or not players.get("away"):raise ValueError("Incomplete player data")
        rec={"game_id":str(game_id),"date":game["date"],"season":int(game["date"][:4]),"phase":phase,
             "home":{"slug":mapping[hi]["slug"],"mlb_id":hi,"runs":home["runs"]},
             "away":{"slug":mapping[ai]["slug"],"mlb_id":ai,"runs":away["runs"]},
             "player_records":players,"source":game.get("source"),"market":None}
        if game_id in games:
            original=games[game_id]
            for field in ("game_id","date","season","phase","home","away"):
                if original[field]!=rec[field]:raise ValueError("Conflicting historical result "+game_id+" "+field)
            metrics["existing"]+=1
        else:
            games[game_id]=rec;metrics["inserted"]+=1
    metrics["total_archive_games"]=len(games)
    return {"schema_version":1,"status":"INTERNAL_STAGING_ONLY","games":games},dict(metrics)
def main():
    p=argparse.ArgumentParser();p.add_argument("--stage",default="mlb/data/daily-backfill-preview.json");p.add_argument("--crosswalk",default="mlb/data/mlb-team-identity-audit.json");p.add_argument("--existing",default="mlb/data/internal-backfill-archive.json");p.add_argument("--out",default="mlb/data/internal-backfill-archive-preview.json");a=p.parse_args()
    staged=json.loads(Path(a.stage).read_text());cross=json.loads(Path(a.crosswalk).read_text())
    source=Path(a.existing);archive=json.loads(source.read_text()) if source.exists() else {"games":{}}
    result,metrics=merge_archive(archive,staged,cross)
    target=Path(a.out);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"coverage":metrics,"published":False}))
if __name__=="__main__":main()
