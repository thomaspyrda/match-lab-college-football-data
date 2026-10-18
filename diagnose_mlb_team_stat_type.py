#!/usr/bin/env python3
"""One-team-only probe to find missing 2025 team player batting splits.

Uses two alternative official MLB Stats API stat types. Diagnostics never publish
and do not treat an incomplete response as validated.
"""
import json
from pathlib import Path
from test_mlb_postseason_backfill import fetch
from diagnose_mlb_player_query_coverage import summarize, FIELDS

YEAR=2025
TEAM=109

def run(fetcher=fetch):
    queries={
      "season_current":f"/stats?stats=season&group=hitting&season={YEAR}&teamId={TEAM}&playerPool=ALL&limit=1000",
      "year_by_year_by_team":f"/stats?stats=yearByYearByTeam&group=hitting&season={YEAR}&teamId={TEAM}&playerPool=ALL&limit=1000",
    }
    team_payload=fetcher(f"/teams/{TEAM}/stats?stats=season&group=hitting&season={YEAR}")
    splits=[s for b in team_payload.get("stats",[]) for s in b.get("splits",[])]
    if len(splits)!=1:
        raise ValueError("Official team batting total missing or ambiguous")
    team={key:int(splits[0]["stat"][key]) for key in FIELDS}
    results={}
    for label,url in queries.items():
        payload=fetcher(url)
        parsed=summarize(payload,TEAM)
        results[label]={"records":parsed["records"],"totals":parsed["totals"],
            "deficits":{key:team[key]-parsed["totals"][key] for key in FIELDS},
            "player_ids":parsed["player_ids"]}
    return {"status":"SINGLE_TEAM_API_DIAGNOSTIC_ONLY","team_id":TEAM,
        "season":YEAR,"official_totals":team,"queries":results,"published":False}

if __name__=="__main__":
    result=run()
    target=Path("mlb/data/mlb-single-team-stat-type-diagnostic.json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({**{k:v for k,v in result.items() if k!="queries"},
        "queries":{k:{"records":v["records"],"deficits":v["deficits"]} for k,v in result["queries"].items()}}))
