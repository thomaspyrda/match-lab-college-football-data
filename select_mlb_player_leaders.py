#!/usr/bin/env python3
"""Select prominent MLB team-season leaders from staged team-specific splits.

Only a leaders selection, NEVER a complete-roster or team-total reconciliation.
Do not publish without confirming source coverage of prominent players.
"""
import argparse,json
from pathlib import Path

def choose(dataset):
    if dataset.get("complete") is not True:
        raise ValueError("Incomplete player-stat source")
    output={"team_id":dataset["team_id"],"season":dataset["season"]}
    groups=dataset["groups"]
    for kind in ("hitting","pitching"):
        if kind not in groups:raise ValueError("Missing "+kind)
        for r in groups[kind]["records"]:
            if r.get("team_id")!=dataset["team_id"] or r.get("attribution")!="explicit_team_split":
                raise ValueError("Unverified team split")
    hitters=groups["hitting"]["records"]
    def number(row,key):
        raw=row["stats"].get(key)
        if raw is None:raise ValueError("Missing "+key+" for player "+str(row["player_id"]))
        return int(raw)
    # At-bats are the ONLY performance criterion. Player ID breaks exact AB ties deterministically.
    ranked_hitters=sorted(hitters,key=lambda r:(-number(r,"atBats"),r["player_id"]))
    pitchers=groups["pitching"]["records"]
    for row in pitchers:
        appearances=number(row,"gamesPlayed")
        starts=number(row,"gamesStarted")
        if starts<0 or appearances<starts:raise ValueError("Invalid pitching appearances")
    starters=sorted(pitchers,key=lambda r:(-number(r,"gamesStarted"),-number(r,"gamesPlayed"),r["player_id"]))[:5]
    relievers=sorted(pitchers,key=lambda r:(-(number(r,"gamesPlayed")-number(r,"gamesStarted")),r["player_id"]))
    starter_ids={r["player_id"] for r in starters}
    relievers=[r for r in relievers if r["player_id"] not in starter_ids][:8]
    output.update({"top_hitters":ranked_hitters[:20],"starting_pitchers":starters,"relief_pitchers":relievers,
                   "selection_policy":"top_20_team_at_bats_top_5_starts_top_5_relief_appearances",
                   "hitter_selection_basis":"team_specific_season_at_bats_only",
                   "hitter_tie_breaker":"player_id_only_when_at_bats_equal",
                   "full_roster_reconciled":False,"published":False})
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--year",type=int,default=2025)
    p.add_argument("--input",default=None)
    p.add_argument("--out",default=None)
    a=p.parse_args()
    source=json.loads(Path(a.input or f"mlb/data/mlb-player-league-{a.year}.json").read_text())
    if source["season"]!=a.year:raise ValueError("Season mismatch")
    datasets=source["team_datasets"]
    if len(datasets)!=30:raise ValueError("Require all 30 MLB teams")
    result={"status":"PLAYER_LEADERS_STAGING_ONLY","season":source["season"],
            "teams":{d["team_id"]:choose(d) for d in datasets},"published":False}
    path=Path(a.out or f"mlb/data/mlb-player-leaders-{a.year}.json");path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"teams":len(result["teams"]),
        "hitters":sum(len(v["top_hitters"]) for v in result["teams"].values()),
        "starting_pitchers":sum(len(v["starting_pitchers"]) for v in result["teams"].values()),
        "relief_pitchers":sum(len(v["relief_pitchers"]) for v in result["teams"].values()),"published":False}))
if __name__=="__main__":main()
