#!/usr/bin/env python3
"""Read-only orchestration contract checks; never rewrites sport data or site visuals."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "nba": ["nba/dashboard/data/dashboard.json", "nba/rankings/data/nba-team-rankings.json",
            "nba/teams/data/current-season.json", "nba/teams/data/current-schedule.json", "nba/season-leaders/data/leaders.json"],
    "cbb": ["cbb/dashboard/data/dashboard.json", "data/cbb/strength-rankings.json"],
    "cfb": ["cfb-dashboard-preview/data/dashboard.json"],
    "mlb": ["mlb/dashboard/data/dashboard.json"],
}

def verify_nba_schedule_results(schedule, dashboard):
    expected = set(dashboard.get("freshness", {}).get("expected_previous_day_games", []))
    matches = {gid: [] for gid in expected}
    for slug, team in schedule.get("teams", {}).items():
        for game in team.get("games", []):
            gid = str(game.get("game_id"))
            if gid in matches:
                if game.get("result") not in ("W", "L") or game.get("score_for") is None or game.get("score_against") is None:
                    raise ValueError(f"NBA team schedule missing verified final result: {slug} {gid}")
                matches[gid].append(game)
    for gid, rows in matches.items():
        if len(rows) != 2:
            raise ValueError(f"NBA final result must appear on both team schedules: {gid}")
        a, b = rows
        if (a["score_for"], a["score_against"]) != (b["score_against"], b["score_for"]) or a["result"] == b["result"]:
            raise ValueError(f"NBA team schedule score disagreement: {gid}")
    return len(expected)

def validate(sport):
    reports = []
    for filename in SOURCES[sport]:
        path = ROOT / filename
        if not path.is_file():
            raise SystemExit(f"{sport}: required published dataset missing: {filename}")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not data:
            raise SystemExit(f"{sport}: empty or invalid data: {filename}")
        reports.append({"file": filename, "bytes": path.stat().st_size,
                        "updated_at": data.get("updated_at") or data.get("generated_at"),
                        "data_through": data.get("data_through") or data.get("checked_through")})
    if sport == "nba":
        schedule = json.loads((ROOT / "nba/teams/data/current-schedule.json").read_text())
        dashboard = json.loads((ROOT / "nba/dashboard/data/dashboard.json").read_text())
        reports.append({"verified_previous_day_results_on_both_team_schedules": verify_nba_schedule_results(schedule, dashboard)})
    if sport == "cbb":
        teams = sorted((ROOT / "data/cbb/teams").glob("*.json"))
        if len(teams) < 350:
            raise SystemExit(f"CBB team archive incomplete: {len(teams)} team files")
        for path in teams:
            data = json.loads(path.read_text(encoding="utf-8"))
            season = data.get("seasons", {}).get("2027")
            if not season:
                raise SystemExit(f"Missing active CBB season: {path.name}")
            for phase in season.get("phases", {}).values():
                final = [g for g in phase.get("games", []) if g.get("status") == "final"]
                if any(g.get("points") is None or g.get("opponent_points") is None for g in final):
                    raise SystemExit(f"Final game missing score: {path.name}")
                if phase.get("completed_games") != len(final):
                    raise SystemExit(f"Completed-game count mismatch: {path.name}")
        reports.append({"verified_team_archive_files": len(teams)})
    print(json.dumps({"sport":sport, "read_only":True, "reports":reports},indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sport", choices=sorted(SOURCES), required=True)
    validate(parser.parse_args().sport)
