#!/usr/bin/env python3
"""Audit archived college basketball market records without promoting unverified games."""
import json
from pathlib import Path
root=Path("data/cbb/markets")
summary={"team_archives":0,"market_game_records":0,"with_spread":0,"with_total":0,"with_ou_label":0,"with_timestamp":0,"verified_pregame_snapshots":0}
for path in sorted(root.glob("*.json")):
    d=json.loads(path.read_text())
    summary["team_archives"]+=1
    for season,games in d.get("games",{}).items():
        if not isinstance(games,dict):continue
        for gid,rec in games.items():
            if not isinstance(rec,dict):continue
            summary["market_game_records"]+=1
            summary["with_spread"]+=int(rec.get("spread") is not None)
            summary["with_total"]+=int(rec.get("total") is not None)
            summary["with_ou_label"]+=int(rec.get("ou") in ("O","U","P"))
            summary["with_timestamp"]+=int(bool(rec.get("observed_at")))
print(json.dumps(summary,indent=2))
print("NOTE: per-team records may duplicate games. Market lines and O/U labels do not certify pregame team metrics.")
Path("cbb/match-lab/data/market-coverage-audit.json").write_text(json.dumps(summary,indent=2)+"\n")
