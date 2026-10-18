#!/usr/bin/env python3
"""Read-only targeted check of MLB starting/relief leader coverage against fresh source splits."""
import argparse
import json
from pathlib import Path
from test_mlb_postseason_backfill import fetch
from audit_mlb_historical_leader_coverage import get_splits, integer

def verify_pitchers(archive, year, team_id, fetcher=fetch):
    staged = archive["teams"][str(team_id)][str(year)]
    url = f"/stats?stats=season&group=pitching&season={year}&teamId={team_id}&limit=1000"
    records = list(get_splits(fetcher(url), team_id).values())
    if not records:
        raise ValueError("No pitching records returned")
    for row in records:
        gp, gs = integer(row, "gamesPlayed"), integer(row, "gamesStarted")
        if gs < 0 or gp < gs:
            raise ValueError("Invalid appearances for player " + str(row["player_id"]))
    expected_starters = sorted(records, key=lambda r: (-integer(r, "gamesStarted"),
                            -integer(r, "gamesPlayed"), r["player_id"]))[:5]
    starter_ids = {r["player_id"] for r in expected_starters}
    expected_relief = sorted((r for r in records if r["player_id"] not in starter_ids),
                            key=lambda r: (-(integer(r, "gamesPlayed") -
                                             integer(r, "gamesStarted")), r["player_id"]))[:5]
    selected_starters = staged["starters"]
    selected_relief = staged["relievers"]
    comparison = {}
    for label, selected, reference in (("starters", selected_starters, expected_starters),
                                       ("relievers", selected_relief, expected_relief)):
        a = [r["player_id"] for r in selected]
        b = [r["player_id"] for r in reference]
        discrepancies = []
        ref_by_id = {r["player_id"]: r for r in reference}
        for player in selected:
            actual = ref_by_id.get(player["player_id"])
            if actual is None:
                continue
            for field in ("gamesPlayed", "gamesStarted"):
                if integer(player, field) != integer(actual, field):
                    discrepancies.append({"player_id": player["player_id"],
                                          "field": field,
                                          "stage": integer(player, field),
                                          "reference": integer(actual, field)})
        comparison[label] = {"matches": a == b and not discrepancies,
                             "staged_ids": a if a != b else [],
                             "expected_ids": b if a != b else [],
                             "stat_mismatches": discrepancies}
    return {"season": year, "team_id": str(team_id), "reference_pitchers": len(records),
            "passed": all(v["matches"] for v in comparison.values()),
            "groups": comparison, "reference_endpoint": url}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--years", required=True)
    parser.add_argument("--team-ids", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    archive = json.loads(Path(args.input).read_text())
    if archive.get("status") != "MLB_HISTORICAL_LEADERS_REVIEW_ONLY" or archive.get("published") is not False:
        raise ValueError("Requires unpublished review archive")
    years = sorted({int(x) for x in args.years.split(",")})
    tids = sorted({int(x) for x in args.team_ids.split(",")})
    if not years or not tids or any(y < 2015 or y > 2026 for y in years):
        raise ValueError("Invalid audit scope")
    results = []
    for year in years:
        for tid in tids:
            try:
                results.append(verify_pitchers(archive, year, tid))
            except Exception as exc:
                results.append({"season": year, "team_id": str(tid), "passed": False,
                                "error_type": type(exc).__name__, "error": str(exc)})
    summary = {"status": "MLB_PITCHER_COVERAGE_REVIEW_ONLY",
               "checks": len(results), "passed": sum(bool(x["passed"]) for x in results),
               "failed": sum(not x["passed"] for x in results), "published": False,
               "source": "MLB Stats API alternate query; not third-party verification",
               "results": results}
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}))
    if summary["failed"]:
        raise SystemExit("Pitcher leader comparison discrepancies detected; publication blocked")

if __name__ == "__main__":
    main()
