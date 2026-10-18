#!/usr/bin/env python3
"""Read-only audit of staged MLB player batting totals against official team totals."""
import argparse,json
from pathlib import Path
from test_mlb_postseason_backfill import fetch

FIELDS=("atBats","hits","homeRuns","rbi")
def reconcile(stage,fetcher=fetch):
    year=stage["season"]; results={}
    for team in stage["team_datasets"]:
        tid=team["team_id"]
        rows=team["groups"]["hitting"]["records"]
        computed={field:sum(int(r["stats"].get(field,0) or 0) for r in rows) for field in FIELDS}
        response=fetcher(f"/teams/{tid}/stats?stats=season&group=hitting&season={year}")
        splits=[s for block in response.get("stats",[]) for s in block.get("splits",[])]
        if len(splits)!=1:raise ValueError("Missing or ambiguous official team stats: "+tid)
        actual=splits[0].get("stat",{})
        expected={field:int(actual[field]) for field in FIELDS if actual.get(field) is not None}
        if len(expected)!=len(FIELDS):raise ValueError("Incomplete team hitting totals: "+tid)
        mismatches={field:{"player_sum":computed[field],"team_total":expected[field]}
            for field in FIELDS if computed[field]!=expected[field]}
        results[tid]={"player_sums":computed,"official_totals":expected,"mismatches":mismatches}
    return {"status":"TEAM_HITTING_RECONCILIATION_NO_PUBLICATION","season":year,
        "teams_checked":len(results),"teams_matching":sum(not x["mismatches"] for x in results.values()),
        "teams":results,"published":False}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",default="mlb/data/mlb-player-league-2025.json")
    p.add_argument("--out",default="mlb/data/mlb-player-team-hitting-audit-2025.json")
    args=p.parse_args()
    result=reconcile(json.loads(Path(args.input).read_text()))
    target=Path(args.out);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="teams"}))
    for tid,team in result["teams"].items():
        if team["mismatches"]:
            print(json.dumps({"team_id":tid,"mismatches":team["mismatches"]}))
    if result["teams_checked"]!=30 or result["teams_matching"]!=30:
        raise SystemExit("MLB player/team batting mismatch: no publication")
if __name__=="__main__":main()
