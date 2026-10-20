#!/usr/bin/env python3
"""Add official MLB team season metrics without changing archived schedule/results."""
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data/mlb/season-snapshots.json"
TEAM_IDS = {
    108: "los-angeles-angels", 109: "arizona-diamondbacks", 110: "baltimore-orioles",
    111: "boston-red-sox", 112: "chicago-cubs", 113: "cincinnati-reds",
    114: "cleveland-guardians", 115: "colorado-rockies", 116: "detroit-tigers",
    117: "houston-astros", 118: "kansas-city-royals", 119: "los-angeles-dodgers",
    120: "washington-nationals", 121: "new-york-mets", 133: "athletics",
    134: "pittsburgh-pirates", 135: "san-diego-padres", 136: "seattle-mariners",
    137: "san-francisco-giants", 138: "st-louis-cardinals", 139: "tampa-bay-rays",
    140: "texas-rangers", 141: "toronto-blue-jays", 142: "minnesota-twins",
    143: "philadelphia-phillies", 144: "atlanta-braves", 145: "chicago-white-sox",
    146: "miami-marlins", 147: "new-york-yankees", 158: "milwaukee-brewers",
}
METRICS = (
    "batting_average", "on_base_percentage", "slugging_percentage", "home_runs",
    "strikeout_rate", "era", "whip", "opponent_average", "bullpen_era",
    "strikeouts_per_9",
)


def fetch_group(year, group, sit_codes=None):
    params = {
        "season": str(year),
        "stats": "season",
        "group": group,
        "sportIds": "1",
        "gameType": "R",
    }
    if sit_codes:
        params["sitCodes"] = sit_codes
    query = urllib.parse.urlencode(params)
    url = "https://statsapi.mlb.com/api/v1/teams/stats?" + query
    request = urllib.request.Request(url, headers={"User-Agent": "BetWiseResearch/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                document = json.load(response)
            rows = {}
            for stat_group in document.get("stats", []):
                for split in stat_group.get("splits", []):
                    team_id = split.get("team", {}).get("id")
                    if team_id in TEAM_IDS:
                        rows[team_id] = split.get("stat", {})
            if len(rows) < 25:
                raise ValueError(f"{group} {year} returned only {len(rows)} MLB teams from {url}")
            return rows, url
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def round_metric(value, digits):
    return round(value, digits) if value is not None else None


def metrics_for(hitting, pitching, bullpen):
    pa = number(hitting.get("plateAppearances"))
    strikeouts = number(hitting.get("strikeOuts"))
    strikeout_rate = (strikeouts / pa * 100) if pa and strikeouts is not None else None
    return {
        "batting_average": round_metric(number(hitting.get("avg")), 3),
        "on_base_percentage": round_metric(number(hitting.get("obp")), 3),
        "slugging_percentage": round_metric(number(hitting.get("slg")), 3),
        "home_runs": int(number(hitting.get("homeRuns"))) if number(hitting.get("homeRuns")) is not None else None,
        "strikeout_rate": round_metric(strikeout_rate, 1),
        "era": round_metric(number(pitching.get("era")), 2),
        "whip": round_metric(number(pitching.get("whip")), 2),
        "opponent_average": round_metric(number(pitching.get("avg")), 3),
        "bullpen_era": round_metric(number(bullpen.get("era")), 2),
        "strikeouts_per_9": round_metric(number(pitching.get("strikeoutsPer9Inn")), 2),
    }


def main():
    snapshot = json.loads(DATA_PATH.read_text())
    seasons = snapshot.get("seasons", {})
    filled = 0
    missing = []
    for year_text, teams in sorted(seasons.items(), key=lambda item: int(item[0])):
        year = int(year_text)
        if not any(
            not isinstance(row.get("team_stats"), dict)
            or any(row["team_stats"].get(key) is None for key in METRICS)
            for row in teams.values()
        ):
            continue
        hitting, hitting_url = fetch_group(year, "hitting")
        pitching, pitching_url = fetch_group(year, "pitching")
        bullpen, bullpen_url = fetch_group(year, "pitching", "rel")
        fetched_at = datetime.now(timezone.utc).isoformat()
        for team_id, slug in TEAM_IDS.items():
            row = teams.get(slug)
            if row is None:
                continue
            values = metrics_for(
                hitting.get(team_id, {}),
                pitching.get(team_id, {}),
                bullpen.get(team_id, {}),
            )
            existing = row.get("team_stats")
            if not isinstance(existing, dict):
                existing = {}
                row["team_stats"] = existing
            changed = False
            for key in METRICS:
                if existing.get(key) is None and values[key] is not None:
                    existing[key] = values[key]
                    changed = True
                if existing.get(key) is None:
                    missing.append(f"{year}:{slug}:{key}")
            if changed:
                row["team_stats_source"] = {
                    "provider": "MLB Stats API",
                    "hitting": hitting_url,
                    "pitching": pitching_url,
                    "bullpen": bullpen_url,
                }
                row["team_stats_updated_at"] = fetched_at
                filled += 1
        print(year, "stats fetched for", len(hitting), "hitting teams,", len(pitching), "pitching teams,", len(bullpen), "bullpen teams")
    DATA_PATH.write_text(json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False) + "\n")
    print("Updated team rows:", filled)
    if missing:
        print("Metrics still unavailable:", len(missing), "(first 12)", ", ".join(missing[:12]))
    else:
        print("All requested MLB team-season metrics are populated.")


if __name__ == "__main__":
    main()
