#!/usr/bin/env python3
"""Audit team-specific player season splits across two MLB teams; read-only."""
import argparse,json
from pathlib import Path
from probe_mlb_player_season_stats import probe

def audit(probes):
    seen={}
    records=0
    for dataset in probes:
        year=dataset["season"]
        for group,details in dataset["groups"].items():
            for row in details["records"]:
                key=(year,group,row["player_id"],row["team_id"])
                if key in seen:raise ValueError("Duplicate player/team/season/group split")
                if row.get("attribution")!="explicit_team_split" or row["team_id"]!=dataset["team_id"]:
                    raise ValueError("Unverified team attribution")
                seen[key]=row
                records+=1
    multi={}
    for key,row in seen.items():
        season,group,pid,team=key
        lookup=(season,group,pid)
        multi.setdefault(lookup,set()).add(team)
    shared=[{"season":y,"group":group,"player_id":pid,"teams":sorted(teams)}
        for (y,group,pid),teams in multi.items() if len(teams)>1]
    return {"status":"MULTI_TEAM_AUDIT_NO_PUBLICATION","teams_audited":len(probes),
        "records":records,"cross_team_players":shared,"published":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",type=int,default=2025)
    p.add_argument("--team-ids",default="144,147")
    p.add_argument("--out",default="mlb/data/cross-team-player-audit-2025.json")
    a=p.parse_args()
    teams=[int(x) for x in a.team_ids.split(",")]
    if len(teams)!=len(set(teams)) or len(teams)<2:raise ValueError("Distinct teams required")
    result=audit([probe(a.year,t) for t in teams])
    path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"teams_audited":result["teams_audited"],
        "records":result["records"],"cross_team_player_count":len(result["cross_team_players"]),"published":False}))
if __name__=="__main__":main()
