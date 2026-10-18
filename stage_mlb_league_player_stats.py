#!/usr/bin/env python3
"""Stage one MLB season of team-specific player stats for all 30 teams; no publication."""
import argparse,json
from pathlib import Path
from probe_mlb_player_season_stats import probe
from audit_mlb_multi_team_player_stats import audit

def collect(year,crosswalk,fetcher=None):
    mapping=crosswalk.get("teams",{})
    if len(mapping)!=30 or len({row["slug"] for row in mapping.values()})!=30:
        raise ValueError("Complete 30-team identity audit required")
    datasets=[]
    for team_id in sorted(mapping,key=int):
        kwargs={"fetcher":fetcher} if fetcher is not None else {}
        result=probe(year,int(team_id),**kwargs)
        if not result["complete"]:
            raise ValueError("Missing hitting or pitching records for "+team_id)
        for group in ("hitting","pitching"):
            details=result["groups"][group]
            if any(v for v in details["missing_core_fields"].values()):
                raise ValueError("Core player stat missing: "+team_id+" "+group)
        datasets.append(result)
    report=audit(datasets)
    report["season"]=year
    report["team_coverage"]={mapping[d["team_id"]]["slug"]:{
        group:d["groups"][group]["count"] for group in ("hitting","pitching")} for d in datasets}
    report["status"]="LEAGUE_PLAYER_STATS_STAGED_NO_PUBLICATION"
    report["team_datasets"]=datasets
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",type=int,default=2025)
    p.add_argument("--crosswalk",default="mlb/data/mlb-team-identity-audit.json")
    p.add_argument("--out",default=None)
    a=p.parse_args()
    result=collect(a.year,json.loads(Path(a.crosswalk).read_text()))
    path=Path(a.out or f"mlb/data/mlb-player-league-{a.year}.json");path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"season":a.year,
       "teams":len(result["team_coverage"]),"records":result["records"],
       "cross_team_player_count":len(result["cross_team_players"]),"published":False}))
if __name__=="__main__":main()
