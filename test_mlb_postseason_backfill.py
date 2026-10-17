#!/usr/bin/env python3
"""Read-only MLB postseason backfill smoke test. No production publishing.

MLB Stats API schedule, final scores, and live box scores. Source usage
permissions for public redistribution must be reviewed separately.
"""
import argparse,json,urllib.request
from collections import Counter
from datetime import date,datetime,timezone,timedelta
from pathlib import Path
from daily_backfill_core import GameObservation

BASE="https://statsapi.mlb.com/api/v1"
def fetch(path):
    req=urllib.request.Request(BASE+path,headers={"User-Agent":"BetWise research data-feed validation/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as r:return json.load(r)
def run(start,end):
    games=fetch(f"/schedule?sportId=1&startDate={start}&endDate={end}&hydrate=linescore&gameTypes=D,L,W,F")["dates"]
    seen=set();summary=Counter();samples=[];failures=[];warnings=[]
    for day in games:
        for game in day.get("games",[]):
            gid=game["gamePk"]
            if gid in seen:raise ValueError("duplicate game id")
            seen.add(gid);summary["scheduled_games"]+=1
            status=game.get("status",{}).get("abstractGameState")
            if status!="Final":
                summary["not_final"]+=1;continue
            sides=game["teams"];home=sides["home"];away=sides["away"]
            if "score" not in home or "score" not in away:
                summary["unscored_final_status"]+=1\n                warnings.append(f"{gid}: marked final but no schedule score; not imported");continue
            dt=game.get("officialDate") or game["gameDate"][:10]
            observed=datetime.now(timezone.utc).isoformat()
            GameObservation("mlb",str(gid),observed,dt,str(home["team"]["id"]),str(away["team"]["id"]),"final",int(home["score"]),int(away["score"])).validate()
            box=fetch(f"/game/{gid}/boxscore")
            teams=box.get("teams",{})
            if not teams.get("home",{}).get("players") or not teams.get("away",{}).get("players"):
                failures.append(f"{gid}: missing boxscore players");continue
            summary["validated_final_games"]+=1
            summary["player_records"]+=sum(len(teams[side]["players"]) for side in ("home","away"))
            if len(samples)<8:samples.append({"game_id":gid,"date":dt,"away_id":away["team"]["id"],"home_id":home["team"]["id"],"away_runs":away["score"],"home_runs":home["score"],"home_players":len(teams["home"]["players"]),"away_players":len(teams["away"]["players"])})
    return {"status":"READ_ONLY_NO_PUBLICATION","source":"MLB Stats API","date_from":start,"date_to":end,"summary":dict(summary),"samples":samples,"errors":failures,"warnings":warnings}
def main():
    p=argparse.ArgumentParser();p.add_argument("--start",default="2026-10-12");p.add_argument("--end",default="2026-10-17");p.add_argument("--out",default="mlb/data/postseason-backfill-smoke-test.json");args=p.parse_args()
    report=run(args.start,args.end);path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))
    if report["errors"] or not report["summary"].get("validated_final_games"):raise SystemExit("MLB backfill smoke test incomplete")
if __name__=="__main__":main()
