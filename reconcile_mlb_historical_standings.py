#!/usr/bin/env python3
"""Reconcile staged MLB seasons to official standings; read-only and fail closed."""
import argparse,json
from pathlib import Path
from test_mlb_postseason_backfill import fetch

def reconcile(stage,crosswalk,standings):
    year=stage["season"]
    mapping=crosswalk["teams"]
    byid={str(k):v["slug"] for k,v in mapping.items()}
    expected={}
    for rec in standings.get("records",[]):
        for row in rec.get("teamRecords",[]):
            slug=byid.get(str(row["team"]["id"]))
            if slug:
                expected[slug]=(int(row["wins"]),int(row["losses"]))
    if len(expected)!=30:
        raise ValueError("Standings incomplete: "+str(len(expected))+" teams")
    actual={slug:[0,0,0] for slug in expected}
    for gid,g in stage["games"].items():
        if g["phase"]!="regular":continue
        h=g["home"];a=g["away"];hs=h["runs"];aw=a["runs"]
        if h["slug"] not in actual or a["slug"] not in actual:
            raise ValueError("Unknown team in "+gid)
        if hs==aw:
            actual[h["slug"]][2]+=1
            actual[a["slug"]][2]+=1
        else:
            actual[h["slug"]][int(hs<aw)]+=1
            actual[a["slug"]][int(aw<hs)]+=1
    teams={}
    for slug,exp in sorted(expected.items()):
        wins,losses,ties=actual[slug]
        teams[slug]={"actual":{"wins":wins,"losses":losses,"ties":ties},
                     "official":{"wins":exp[0],"losses":exp[1]},
                     "match":(wins,losses)==exp}
    return {"status":"RECONCILIATION_ONLY","year":year,"teams_checked":30,
        "teams_matching":sum(t["match"] for t in teams.values()),
        "teams_mismatching":[slug for slug,t in teams.items() if not t["match"]],
        "teams":teams,"published":False}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",type=int,required=True)
    p.add_argument("--stage",default=None)
    p.add_argument("--crosswalk",default="mlb/data/mlb-team-identity-audit.json")
    args=p.parse_args()
    stage=json.loads(Path(args.stage or f"mlb/data/historical-stage-{args.year}.json").read_text())
    cross=json.loads(Path(args.crosswalk).read_text())
    standings=fetch(f"/standings?leagueId=103,104&season={args.year}&standingsTypes=regularSeason")
    result=reconcile(stage,cross,standings)
    path=Path(f"mlb/data/historical-reconciliation-{args.year}.json")
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({k:v for k,v in result.items() if k!="teams"}))
    if result["teams_matching"]!=30:
        raise SystemExit("Standings reconciliation incomplete; no publication")
if __name__=="__main__":main()
