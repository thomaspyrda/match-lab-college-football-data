#!/usr/bin/env python3
"""Read-only MLB player season-stat API probe. No live page writes.

Use a single team and season initially. The public MLB Stats API endpoint is
probed independently for hitting and pitching; failed/empty responses are
reported as incomplete and are never represented as verified player coverage.
"""
import argparse,json
from pathlib import Path
from test_mlb_postseason_backfill import fetch

GROUPS=("hitting","pitching")
def probe(year,team_id,fetcher=fetch):
    if not 2015<=year<=2026:raise ValueError("Invalid MLB season")
    if not 1<=int(team_id)<=9999:raise ValueError("Invalid MLB team ID")
    groups={}
    for group in GROUPS:
        url=f"/stats?stats=season&group={group}&season={year}&teamId={team_id}&playerPool=ALL&limit=1000"
        payload=fetcher(url)
        rows=[]
        for block in payload.get("stats",[]):
            for split in block.get("splits",[]):
                player=split.get("player") or {}
                pid=player.get("id")
                stat=split.get("stat") or {}
                if not pid or not stat:continue
                if split.get("team") and str(split["team"].get("id"))!=str(team_id):continue
                rows.append({"player_id":int(pid),"name":player.get("fullName"),
                  "team_id":str(team_id),"season":year,"group":group,"stats":stat})
        unique={p["player_id"] for p in rows}
        if len(unique)!=len(rows):raise ValueError("Duplicate player season entries: "+group)
        required=("gamesPlayed","atBats","hits") if group=="hitting" else ("gamesPlayed","inningsPitched","era")
        field_coverage={key:sum(row["stats"].get(key) is not None for row in rows) for key in required}
        groups[group]={"records":rows,"count":len(rows),"complete":bool(rows),
            "field_coverage":field_coverage,"missing_core_fields":{
                key:len(rows)-n for key,n in field_coverage.items()},"endpoint":url}
    return {"status":"PLAYER_STATS_PROBE_ONLY_NO_PUBLICATION",
        "season":year,"team_id":str(team_id),"groups":groups,
        "complete":all(g["complete"] for g in groups.values())}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",type=int,default=2025)
    p.add_argument("--team-id",type=int,default=144,help="MLB team ID (144 = Atlanta Braves)")
    p.add_argument("--out",default=None)
    a=p.parse_args()
    result=probe(a.year,a.team_id)
    dest=Path(a.out or f"mlb/data/player-stats-probe-{a.year}-{a.team_id}.json");dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"year":a.year,"team_id":a.team_id,
        "hitting":result["groups"]["hitting"]["count"],
        "pitching":result["groups"]["pitching"]["count"],"field_coverage":{g:result["groups"][g]["field_coverage"] for g in GROUPS},"complete":result["complete"],"published":False}))
    if not result["complete"]:raise SystemExit("Player season-stat endpoint probe incomplete; no publication")
if __name__=="__main__":main()
