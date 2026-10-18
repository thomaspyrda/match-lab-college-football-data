#!/usr/bin/env python3
"""One-team, three-request diagnostic of 2025 Arizona batting coverage.

Uses supported season stats, official team totals and the full-season roster.
Absence from the batting stats is a candidate, not proof of missing batting data.
"""
import json
from pathlib import Path
from test_mlb_postseason_backfill import fetch
from diagnose_mlb_player_query_coverage import summarize, FIELDS

YEAR=2025
TEAM=109

def run(fetcher=fetch):
    player_payload=fetcher(f"/stats?stats=season&group=hitting&season={YEAR}&teamId={TEAM}&playerPool=ALL&limit=1000")
    roster_payload=fetcher(f"/teams/{TEAM}/roster?rosterType=fullSeason&season={YEAR}")
    team_payload=fetcher(f"/teams/{TEAM}/stats?stats=season&group=hitting&season={YEAR}")
    splits=[s for b in team_payload.get("stats",[]) for s in b.get("splits",[])]
    if len(splits)!=1:raise ValueError("Official team batting totals missing")
    official={key:int(splits[0]["stat"][key]) for key in FIELDS}
    player=summarize(player_payload,TEAM)
    roster={int(p["person"]["id"]):p["person"].get("fullName") for p in roster_payload.get("roster",[]) if p.get("person",{}).get("id")}
    if not roster:raise ValueError("Full-season team roster missing")
    missing=sorted(set(roster)-set(player["player_ids"]))
    return {"status":"SINGLE_TEAM_ROSTER_COMPARISON_NO_PUBLICATION","team_id":TEAM,"season":YEAR,
        "official_totals":official,"player_totals":player["totals"],
        "deficits":{k:official[k]-player["totals"][k] for k in FIELDS},
        "roster_count":len(roster),"batting_records":player["records"],
        "roster_absent_from_batting":[{"id":pid,"name":roster[pid]} for pid in missing],
        "published":False}

if __name__=="__main__":
    result=run()
    target=Path("mlb/data/mlb-single-team-stat-type-diagnostic.json")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"team_id":TEAM,"deficits":result["deficits"],
        "roster_count":result["roster_count"],"batting_records":result["batting_records"],
        "unmatched_roster_members":len(result["roster_absent_from_batting"]),"published":False}))
