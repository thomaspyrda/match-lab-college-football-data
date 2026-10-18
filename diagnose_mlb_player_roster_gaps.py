#!/usr/bin/env python3
"""Diagnose missing historical MLB player-stat records against full-season rosters.

Read-only diagnostic. A roster appearance does not guarantee a batting
statistical contribution; missing IDs are investigation candidates.
"""
import argparse,json
from pathlib import Path
from test_mlb_postseason_backfill import fetch

def diagnose(stage, reconciliation, fetcher=fetch):
    year=int(stage["season"])
    mismatched={tid:result for tid,result in reconciliation["teams"].items() if result["mismatches"]}
    byid={d["team_id"]:d for d in stage["team_datasets"]}
    reports={}
    for tid,match in mismatched.items():
        payload=fetcher(f"/teams/{tid}/roster?rosterType=fullSeason&season={year}")
        roster=payload.get("roster",[])
        if not roster:raise ValueError("Empty full-season roster for team "+tid)
        roster_players={int(p["person"]["id"]):p["person"].get("fullName") for p in roster
            if p.get("person",{}).get("id")}
        staged_ids={p["player_id"] for p in byid[tid]["groups"]["hitting"]["records"]}
        missing=sorted(set(roster_players)-staged_ids)
        reports[tid]={"roster_count":len(roster_players),"staged_batters":len(staged_ids),
            "roster_players_absent_from_hitting_stats":[{"player_id":p,"name":roster_players[p]} for p in missing],
            "mismatches":match["mismatches"]}
    return {"status":"ROSTER_DIAGNOSTIC_ONLY_NOT_RECONCILED","season":year,
        "teams_with_mismatches":len(reports),"teams":reports,"published":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage",default="mlb/data/mlb-player-league-2025.json")
    p.add_argument("--audit",default="mlb/data/mlb-player-team-hitting-audit-2025.json")
    p.add_argument("--out",default="mlb/data/mlb-hitting-roster-diagnostic-2025.json")
    a=p.parse_args()
    result=diagnose(json.loads(Path(a.stage).read_text()),json.loads(Path(a.audit).read_text()))
    target=Path(a.out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"teams_with_mismatches":result["teams_with_mismatches"],
        "missing_roster_candidates":{tid:len(d["roster_players_absent_from_hitting_stats"]) for tid,d in result["teams"].items()},
        "published":False}))
if __name__=="__main__":main()
