#!/usr/bin/env python3
"""Read-only verification of archived MLB leader selections against fresh MLB Stats API responses.

Input is the consolidated 2015–2026 *review* JSON, not production data.
Only requested years/teams are queried to avoid unnecessary API traffic.
The reference is MLB Stats API; agreement is source-consistency evidence,
not independent third-party verification. Never writes live team pages.
"""
import argparse
import json
from pathlib import Path

from test_mlb_postseason_backfill import fetch

def integer(row, field):
    value = row.get("stats", {}).get(field)
    if value is None:
        raise ValueError("Missing " + field)
    return int(value)

def get_splits(payload, team_id):
    splits = [s for block in payload.get("stats", []) for s in block.get("splits", [])]
    rows = {}
    for split in splits:
        player = split.get("player") or {}
        team = split.get("team") or {}
        if str(team.get("id")) != str(team_id) or not player.get("id"):
            continue
        pid = int(player["id"])
        if pid in rows:
            raise ValueError(f"Duplicate player {pid} for team {team_id}")
        rows[pid] = {"player_id": pid, "stats": split.get("stat") or {}}
    return rows

def verify_team(archive, year, tid, fetcher=fetch):
    staged = archive["teams"][str(tid)][str(year)]
    # Distinct query from the one used to populate the staged leader archive:
    url = f"/stats?stats=season&group=hitting&season={year}&teamId={tid}&limit=1000"
    actual = get_splits(fetcher(url), tid)
    if not actual:
        raise ValueError(f"No reference batters for {year}/{tid}")
    ranked = sorted((r for r in actual.values() if integer(r, "atBats") > 0), key=lambda r: (-integer(r, "atBats"), r["player_id"]))[:20]
    selected = [row for row in staged["hitters"] if integer(row, "atBats") > 0]
    expected_ids = [r["player_id"] for r in ranked]
    staged_ids = [r["player_id"] for r in selected]
    matched_ids = staged_ids == expected_ids
    stat_mismatches = []
    for row in selected:
        ref = actual.get(row["player_id"])
        if ref is None:
            stat_mismatches.append({"player_id": row["player_id"], "issue": "absent_from_reference"})
            continue
        for field in ("atBats", "hits", "homeRuns"):
            source = row["stats"].get(field)
            target = ref["stats"].get(field)
            if source is None or target is None or int(source) != int(target):
                stat_mismatches.append({"player_id": row["player_id"], "field": field, "stage": source, "reference": target})
    return {"season": year, "team_id": str(tid), "stage_count": len(selected), "excluded_zero_ab": len(staged["hitters"]) - len(selected),
            "reference_count": len(actual), "leader_order_matches": matched_ids,
            "expected_player_ids": expected_ids if not matched_ids else [],
            "staged_player_ids": staged_ids if not matched_ids else [],
            "stat_mismatches": stat_mismatches, "passed": matched_ids and not stat_mismatches,
            "reference_endpoint": url}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Consolidated historical leader review JSON")
    parser.add_argument("--years", required=True, help="Comma-delimited year(s); deliberately limited")
    parser.add_argument("--team-ids", default="", help="Optional comma-delimited team IDs")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    archive = json.loads(Path(args.input).read_text())
    if archive.get("status") != "MLB_HISTORICAL_LEADERS_REVIEW_ONLY" or archive.get("published") is not False:
        raise ValueError("Require unpublished consolidated review JSON")
    years = sorted({int(s) for s in args.years.split(",")})
    if not years or any(not 2015 <= y <= 2026 for y in years):
        raise ValueError("Invalid seasons")
    team_ids = sorted({int(s) for s in args.team_ids.split(",")}) if args.team_ids else sorted(map(int, archive["teams"]))
    if not team_ids or any(str(t) not in archive["teams"] for t in team_ids):
        raise ValueError("Invalid team ID")
    reports = []
    for year in years:
        for tid in team_ids:
            reports.append(verify_team(archive, year, tid))
    output = {"status": "MLB_LEADERS_SOURCE_COVERAGE_QA_ONLY",
              "years": years, "teams_per_year": len(team_ids), "checks": len(reports),
              "passed": sum(int(row["passed"]) for row in reports),
              "failed": sum(int(not row["passed"]) for row in reports),
              "source": "MLB Stats API alternative team-filtered hitting query; not third-party verification",
              "published": False, "results": reports}
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({k: v for k, v in output.items() if k != "results"}))
    if output["failed"]:
        raise SystemExit("Discrepancy detected. Publication remains blocked.")

if __name__ == "__main__":
    main()
