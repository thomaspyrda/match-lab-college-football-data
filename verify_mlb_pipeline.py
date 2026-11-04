"""Read-only MLB source freshness and published dashboard verification."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent


def verify_source(doc, year, phase, now, teams=False, hours=30):
    if doc.get("season") != year or doc.get("phase") != phase:
        raise ValueError("Wrong MLB source season or phase")
    age = now-datetime.fromisoformat(doc["collected_at"])
    if not -timedelta(minutes=5) <= age <= timedelta(hours=hours):
        raise ValueError("Stale or future MLB source")
    if teams and len(doc.get("teams", {})) != 30:
        raise ValueError("Incomplete MLB source team coverage")


def main():
    from zoneinfo import ZoneInfo
    now = datetime.now(timezone.utc)
    year = now.astimezone(ZoneInfo("America/New_York")).year
    read = lambda path: json.loads((ROOT/path).read_text())
    dashboard = read("mlb/dashboard/data/dashboard.json")
    phase = {"Preseason":1, "Regular season":2, "Postseason":3}[dashboard["season_type"]]
    assert dashboard["season"] == str(year), "Wrong dashboard season"
    verify_source({"season":year,"phase":phase,"collected_at":dashboard["updated_at"]},year,phase,now)
    metrics = read(f"mlb/pipeline/team-metrics-{year}-{phase}.json")
    players = read(f"mlb/pipeline/player-statistics-{year}-{phase}.json")
    markets = read("mlb/pipeline/markets.json")
    lineups = read("mlb/pipeline/lineups.json")
    for source in (metrics,players,markets):
        verify_source(source,year,phase,now,teams=True)
    verify_source(lineups,year,phase,now,hours=18)
    registry = read("data/sports/team-registry.json")
    ids = {str(t["espn_id"]) for t in registry["teams"] if t["sport"] == "mlb"}
    assert len(ids) == 30
    for source in (metrics,players,markets):
        assert set(source["teams"]) == ids, "MLB source population differs from registry"
    assert any(t["games"] > 0 for t in metrics["teams"].values()), "No verified metric samples"
    games = dashboard["games"]
    assert len({str(g["id"]) for g in games}) == len(games), "Duplicate MLB matchups"
    for game in games:
        assert game["away"]["id"] in ids and game["home"]["id"] in ids, "Unregistered MLB matchup team"
        assert game["away"]["id"] != game["home"]["id"], "Invalid matchup"
        for side in ("away","home"):
            assert game[side]["profile"]["metrics"] == metrics["teams"][game[side]["id"]]["metrics"], "Dashboard metric source differs"
    location = read("mlb/dashboard/data/location-records.json")
    assert set(location["teams"]) == ids, "Missing MLB location population"
    verify_source({"season":year,"phase":phase,"collected_at":location["updated_at"]},year,phase,now)
    print(json.dumps({"read_only":True,"season":year,"phase":phase,"teams":len(ids),"matchups":len(games),
                      "ranked_teams":sum(t["games"] > 0 for t in metrics["teams"].values()),
                      "player_records":sum(len(t) for t in players["teams"].values()),
                      "quoted_games":len(markets["quotes"]),"offseason_empty_slate":not bool(games)}))


if __name__ == "__main__":
    main()
