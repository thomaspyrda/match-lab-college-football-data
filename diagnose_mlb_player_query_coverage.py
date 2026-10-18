#!/usr/bin/env python3
"""Compare alternate official MLB player hitting queries for a discrepant team.
Diagnostic only. Never substitutes estimates or changes published records.
"""
import json
from pathlib import Path
from test_mlb_postseason_backfill import fetch
FIELDS=("atBats","hits","homeRuns","rbi")
def summarize(payload,team_id):
    rows=[split for block in payload.get("stats",[]) for split in block.get("splits",[])
          if str((split.get("team") or {}).get("id"))==str(team_id) and split.get("player",{}).get("id")]
    seen=set()
    for r in rows:
        key=r["player"]["id"]
        if key in seen:raise ValueError("Duplicate player row")
        seen.add(key)
    totals={field:sum(int(r.get("stat",{}).get(field,0) or 0) for r in rows) for field in FIELDS}
    return {"records":len(rows),"totals":totals,"player_ids":sorted(seen)}
def run(year=2025,team_id=109,fetcher=fetch):
    variants={
      "existing":f"/stats?stats=season&group=hitting&season={year}&teamId={team_id}&playerPool=ALL&limit=1000",
      "no_pool":f"/stats?stats=season&group=hitting&season={year}&teamId={team_id}&limit=1000",
      "season_team_endpoint":f"/teams/{team_id}/stats?stats=season&group=hitting&season={year}"
    }
    audit={}
    for name,url in variants.items():
        response=fetcher(url)
        if name=="season_team_endpoint":
            audit[name]={"team_totals":next((s.get("stat",{}) for b in response.get("stats",[]) for s in b.get("splits",[])),None)}
        else:audit[name]=summarize(response,team_id)
    return {"status":"API_QUERY_COMPARISON_ONLY","year":year,"team_id":team_id,"queries":audit,"published":False}
if __name__=="__main__":
    report=run()
    path=Path("mlb/data/mlb-player-query-diagnostic-2025-109.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":report["status"],"team_id":report["team_id"],
        "queries":{k:{key:val for key,val in v.items() if key!="player_ids"} for k,v in report["queries"].items()},
        "published":False}))
