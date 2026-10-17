#!/usr/bin/env python3
"""Daily MLB game backfill staging; never publishes to team pages.

Retains source-observed final scores, player game lines, and audit warnings.
Does not claim a historical market price or redistribute data onto public pages.
"""
import argparse,json
from pathlib import Path
from datetime import datetime,timedelta,timezone
from test_mlb_postseason_backfill import fetch
from daily_backfill_core import GameObservation

def build(start,end,fetcher=fetch):
    dates=fetcher(f"/schedule?sportId=1&startDate={start}&endDate={end}&hydrate=linescore&gameTypes=R,D,L,W,F").get("dates",[])
    records={}; warnings=[]
    for d in dates:
        for game in d.get("games",[]):
            gid=str(game["gamePk"])
            if gid in records:raise ValueError("duplicate MLB game: "+gid)
            if game.get("status",{}).get("abstractGameState")!="Final":continue
            sides=game["teams"];h=sides["home"];a=sides["away"]
            if "score" not in h or "score" not in a:
                warnings.append(gid+": missing scores");continue
            dt=game.get("officialDate") or game["gameDate"][:10]
            observed=datetime.now(timezone.utc).isoformat()
            GameObservation("mlb",gid,observed,dt,str(h["team"]["id"]),str(a["team"]["id"]),"final",int(h["score"]),int(a["score"])).validate()
            box=fetcher(f"/game/{gid}/boxscore")
            sides_box=box.get("teams",{})
            if any(not sides_box.get(side,{}).get("players") for side in ("home","away")):
                warnings.append(gid+": incomplete player box scores");continue
            # Preserve player game stats separately; never claim season averages from a single box.
            players={}
            for side in ("home","away"):
                players[side]=[{"player_id":p.get("person",{}).get("id"),"name":p.get("person",{}).get("fullName"),
                  "batting":p.get("stats",{}).get("batting",{}),"pitching":p.get("stats",{}).get("pitching",{})}
                  for p in sides_box[side]["players"].values() if p.get("person",{}).get("id")]
            records[gid]={"game_id":gid,"date":dt,"game_type":game.get("gameType"),"status":"final",
                "home":{"id":str(h["team"]["id"]),"runs":int(h["score"])},"away":{"id":str(a["team"]["id"]),"runs":int(a["score"])},
                "players":players,"observed_at":observed,"source":"MLB Stats API","market":None}
    return {"status":"STAGED_NOT_PUBLISHED","start":start,"end":end,"games":records,
            "coverage":{"validated_games":len(records),"player_records":sum(len(p) for g in records.values() for p in g["players"].values()),"warnings":len(warnings)},"warnings":warnings}

def main():
    p=argparse.ArgumentParser();p.add_argument("--lookback-days",type=int,default=3);p.add_argument("--out",default="mlb/data/daily-backfill-preview.json")
    args=p.parse_args()
    if not 1<=args.lookback_days<=14:raise ValueError("lookback must be 1-14 days")
    today=datetime.now(timezone.utc).date();report=build(str(today-timedelta(days=args.lookback_days)),str(today))
    target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"coverage":report["coverage"],"dates":[report["start"],report["end"]],"status":report["status"]}))
if __name__=="__main__":main()
