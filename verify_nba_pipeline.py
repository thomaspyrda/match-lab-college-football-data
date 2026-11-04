"""Read-only NBA freshness, publication and source-consistency verification."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from validate_nba_refresh import validate

ROOT = Path(__file__).resolve().parent


def fresh(value, now, hours=30):
    age = now - datetime.fromisoformat(value.replace("Z", "+00:00"))
    if age < -timedelta(minutes=5) or age > timedelta(hours=hours):
        raise ValueError("Stale or future-dated NBA observation")


def matching_counts(verified, rankings, current, leaders):
    if any(value != verified for value in (rankings, current, leaders)):
        raise ValueError("NBA completed-game publications do not agree")


def main():
    read = lambda path: json.loads((ROOT / path).read_text())
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo("America/New_York"))
    year = local.year + (local.month >= 7)
    cache = read("nba/dashboard/data/completed-games.json")
    rankings = read("nba/rankings/data/nba-team-rankings.json")
    current = read("nba/teams/data/current-season.json")
    schedule = read("nba/teams/data/current-schedule.json")
    report = validate(cache, rankings, current, schedule, local)
    dashboard = read("nba/dashboard/data/dashboard.json")
    leaders = read("nba/season-leaders/data/leaders.json")
    phase = {"Preseason": 1, "Regular season": 2, "Playoffs": 3}[dashboard["season_type"]]
    games = [g for g in cache["games"] if g["season"] == year and g["phase"] == 2]
    matching_counts(len(games), rankings["seasons"][str(year)]["completed_games"],
                    current["completed_games"], leaders["completed_games"])
    assert leaders["season"] == current["season"] == year, "Wrong NBA publication season"
    assert len({str(g["id"]) for g in games}) == len(games), "Duplicate completed games"
    assert dashboard["completed_games"] == sum(g["season"] == year and g["phase"] == phase for g in cache["games"]), "Dashboard completed-game count differs"
    for value in (dashboard["updated_at"], leaders["updated_at"], schedule["updated_at"], current["data_updated_at"]):
        fresh(value, now)
    registry = read("data/sports/team-registry.json")
    ids = {str(t["espn_id"]) for t in registry["teams"] if t["sport"] == "nba"}
    rosters = read("nba/pipeline/rosters.json")
    assert rosters["season"] == year and set(rosters["teams"]) == ids and len(ids) == 30, "Incomplete roster population"
    fresh(rosters["collected_at"], now)
    for tid, roster in rosters["teams"].items():
        assert roster["team_id"] == tid and roster["players"], "Invalid roster identity"
        fresh(roster["observed_at"], now)
    availability = read("nba/pipeline/availability.json")
    fresh(availability["collected_at"], now, 18)
    defense = read("nba/rankings/data/defense-by-position.json")
    assert defense["season"] == year and len(defense["teams"]) == 30, "Incomplete positional defense population"
    assert all(set(row) == {"PG", "SG", "SF", "PF", "C"} for row in defense["teams"].values()), "Missing positional defense observations"
    fresh(defense["fetched_at"], now)
    location = read("nba/dashboard/data/location-records.json")
    fresh(location["updated_at"], now)
    slate_teams = {str(g[side]["id"]) for g in dashboard["games"] for side in ("away", "home")}
    assert set(location["teams"]) == slate_teams, "Location records do not cover the current slate"
    report.update(read_only=True, matchups=len(dashboard["games"]), leader_players=leaders["players"],
                  roster_players=sum(len(t["players"]) for t in rosters["teams"].values()),
                  retained_rosters=len(rosters["retained_teams"]), defense_source_date=defense["as_of"])
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
