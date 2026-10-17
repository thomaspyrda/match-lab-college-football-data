#!/usr/bin/env python3
"""Validate MLB Stats API to site-registry team identity; no publishing."""
import argparse,json,re
from pathlib import Path
from test_mlb_postseason_backfill import fetch
ROOT=Path(__file__).resolve().parent
def norm(value):
    return re.sub(r"[^a-z0-9]","",str(value).lower())
def crosswalk(registry,mlb_teams):
    local=[t for t in registry["teams"] if t.get("sport")=="mlb"]
    if len(local)!=30:raise ValueError("Expected 30 MLB registry teams")
    names={}
    for team in local:
        for alias in [team["name"]]:
            key=norm(alias)
            if key in names and names[key]["slug"]!=team["slug"]:raise ValueError("ambiguous site team name")
            names[key]=team
    mapping={}
    for team in mlb_teams:
        key=norm(team.get("name"))
        if key not in names:continue
        dest=names[key]
        if dest["slug"] in {v["slug"] for v in mapping.values()}:raise ValueError("duplicate target team")
        mapping[str(team["id"])]={"slug":dest["slug"],"espn_id":str(dest["espn_id"]),"mlb_id":str(team["id"]),"name":dest["name"]}
    if len(mapping)!=30:raise ValueError(f"Matched {len(mapping)} of 30 teams; block publication")
    return mapping
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",default="mlb/data/mlb-team-identity-audit.json");a=p.parse_args()
    data=json.loads((ROOT/"data/sports/team-registry.json").read_text())
    mapping=crosswalk(data,fetch("/teams?sportId=1").get("teams",[]))
    output={"status":"IDENTITY_AUDIT_ONLY","teams":mapping}
    path=ROOT/a.out;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(output,indent=2)+"\n")
    print(json.dumps({"status":output["status"],"mapped":len(mapping),"sample":list(mapping.values())[:3]}))
if __name__=="__main__":main()
