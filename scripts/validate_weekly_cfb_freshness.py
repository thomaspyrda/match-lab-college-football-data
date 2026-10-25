#!/usr/bin/env python3
"""Fail closed when a scheduled CFB ranking refresh is stale or regresses.
No ranking weights or model calculations are changed here.
"""
import argparse
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
def check(stage):
    board = json.loads((DATA / "current_rankings.json").read_text())
    season = int(board["season"])
    hist = json.loads((DATA / "historical" / f"{season}.json").read_text())
    completed = [g for g in hist["games"] if g.get("result") and g.get("start_date")]
    if not completed:
        raise RuntimeError("CFB historical archive has no completed games")
    now = datetime.now(timezone.utc)
    played = []
    for game in completed:
        ts = datetime.fromisoformat(game["start_date"].replace("Z", "+00:00"))
        if ts <= now:
            played.append((ts, int(game.get("week") or 0)))
    if not played:
        raise RuntimeError("CFB archive has no past completed games")
    newest = max(ts for ts, week in played)
    if now - newest > timedelta(days=8):
        raise RuntimeError(f"CFB results stale: latest completed game {newest.isoformat()}")
    highest = max(week for ts, week in played)
    current = int(board.get("through_week") or 0)
    if highest < current:
        raise RuntimeError(f"CFB week regressed: source {highest}, published {current}")
    if stage == "output":
        if current != highest:
            raise RuntimeError(f"CFB rankings not advanced: output through_week={current}, latest source week={highest}")
        approved = json.loads((DATA / "experiments" / f"approved_four_unit_{season}.json").read_text())
        if int(approved["through_week"]) != current:
            raise RuntimeError("Approved rating experiment is not aligned with publication")
        if approved["model"] != board.get("model", {}).get("version"):
            raise RuntimeError("Frozen model version mismatch")
        teams = board.get("teams", [])
        if len(teams) < 130 or any(t.get("national_strength_rank") is None for t in teams):
            raise RuntimeError("Missing FBS ratings; refusing publication")
    print(f"CFB {stage} validated: season {season}, completed source week {highest}, board week {current}, newest game {newest.isoformat()}")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--stage", required=True, choices=("input", "output"))
    check(p.parse_args().stage)
