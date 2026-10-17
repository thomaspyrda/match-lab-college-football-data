#!/usr/bin/env python3
"""Apply reviewed NBA game manifests to 2026-27 season files only.

Explicit --publish required. Never changes past seasons, and never invents
missing spreads, totals, injuries, box scores, or player-season aggregates.
"""
import argparse, json
from pathlib import Path
from collections import Counter

DATA=Path("nba/teams/data")
def apply_manifest(manifest, directory=DATA, write=False):
    if manifest.get("season")!=2027 or manifest.get("status")!="STAGING_NOT_PUBLISHED":
        raise ValueError("Refusing unexpected season or manifest type")
    teams=manifest.get("teams",{})
    if len(teams)!=30:raise ValueError("Expected 30 NBA teams")
    counts=Counter();output={}
    for slug,rows in sorted(teams.items()):
        path=directory/(slug+"-season-details.json")
        obj=json.loads(path.read_text())
        previous=obj.get("seasons",{}).get("2027",{})
        if not rows and not previous.get("games"):
            if "2027" in obj.get("seasons",{}):
                del obj["seasons"]["2027"]
                output[slug]=(path,obj)
                counts["empty_seasons_cleaned"]+=1
            else:
                counts["unmodified_teams"]+=1
            continue
        old={str(g["game_id"]):g for g in previous.get("games",[])}
        for row in rows:
            game_id=str(row["game_id"])
            if not game_id or not row.get("opponent_slug") or row.get("result") not in ("W","L"):
                raise ValueError("Invalid completed game "+slug+" "+game_id)
            # Do not silently alter results that have already been published.
            if game_id in old:
                g=old[game_id]
                for key in ("date","score_for","score_against","location","opponent_slug"):
                    if g.get(key)!=row.get(key):
                        raise ValueError("Conflicting game "+slug+" "+game_id+" "+key)
                for key in ("spread","total","ats_result","ou_result"):
                    if g.get(key) is None and row.get(key) is not None:g[key]=row[key]
                counts["existing"]+=1
                continue
            g={key:row.get(key) for key in ("game_id","date","location","opponent_slug","result","score_for","score_against","spread","total","ats_result","ou_result","odds_source","odds_observed_at")}
            old[game_id]=g;counts["added"]+=1
        games=sorted(old.values(),key=lambda x:(x["date"],str(x["game_id"])))
        wins=sum(g["result"]=="W" for g in games);losses=sum(g["result"]=="L" for g in games)
        for n,g in enumerate(games,1):
            g["game_number"]=n
            g["record_after"]=str(sum(x["result"]=="W" for x in games[:n]))+"–"+str(sum(x["result"]=="L" for x in games[:n]))
        obj.setdefault("seasons",{})["2027"]={**previous,"season_type":"Regular Season","games_played":len(games),"record":f"{wins}–{losses}","games":games}
        output[slug]=(path,obj)
    if write:
        for path,obj in output.values():
            path.write_text(json.dumps(obj,ensure_ascii=False,separators=(",",":"))+"\n")
    return dict(counts)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--manifest",default="nba/dashboard/data/season-team-backfill-preview.json")
    parser.add_argument("--publish",action="store_true")
    args=parser.parse_args()
    data=json.loads(Path(args.manifest).read_text())
    counts=apply_manifest(data,write=args.publish)
    print(json.dumps({"published":args.publish,"coverage":counts,"teams":30}))
if __name__=="__main__":main()
