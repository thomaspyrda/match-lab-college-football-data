"""Collect MLB team metrics independently, retaining season/phase provenance."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent


def source_path(year, phase):
    return ROOT / f"mlb/pipeline/team-metrics-{year}-{phase}.json"


def load_profiles(path, year, phase, team_ids, now):
    doc = json.loads(path.read_text())
    if doc.get("season") != year or doc.get("phase") != phase or set(doc.get("teams", {})) != set(team_ids):
        raise ValueError("Wrong season, phase or incomplete MLB metric population")
    age = now - datetime.fromisoformat(doc["collected_at"])
    if age < -timedelta(minutes=5) or age > timedelta(hours=30):
        raise ValueError("Stale or future-dated MLB metrics")
    return doc["teams"]


def main():
    from concurrent.futures import ThreadPoolExecutor
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from refresh_mlb_dashboard import get, stamp, categories, profile
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("America/New_York")).date()
    year = today.year
    registry = json.loads((ROOT / "data/sports/team-registry.json").read_text())
    ids = {str(t["espn_id"]) for t in registry["teams"] if t["sport"] == "mlb"}
    if len(ids) != 30:
        raise ValueError("Expected all 30 MLB teams")
    dates = [today + timedelta(days=i) for i in range(-8, 8)]
    with ThreadPoolExecutor(8) as pool:
        boards = list(pool.map(lambda day: get("scoreboard?limit=1000&dates=" + day.strftime("%Y%m%d")), dates))
    events = {e["id"]: e for b in boards for e in b.get("events", []) if all(c["team"]["id"] in ids for c in e["competitions"][0]["competitors"])}
    upcoming = sorted([e for e in events.values() if not e["status"]["type"].get("completed") and stamp(e["date"]) >= now - timedelta(hours=8)], key=lambda e: e["date"])
    phase = upcoming[0]["season"]["type"] if upcoming else (3 if today.month >= 10 else 2)
    def one(tid):
        raw = get(f"teams/{tid}/statistics?season={year}&seasontype={phase}", True)
        requested = raw.get("requestedSeason", raw.get("season", {}))
        if raw and (requested.get("year") != year or requested.get("type") != phase):
            print("Excluded mismatched provider metrics for team", tid) 
            return tid, profile({})
        return tid, profile(categories(raw, year, phase))
    with ThreadPoolExecutor(8) as pool:
        teams = dict(pool.map(one, ids))
    if not any(p["games"] > 0 for p in teams.values()):
        raise ValueError("No verified MLB metric samples")
    path = source_path(year, phase)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"season": year, "phase": phase, "collected_at": now.isoformat(), "teams": teams}, allow_nan=False, separators=(",", ":")) + "\n")
    temporary.replace(path)
    print("Collected 30 MLB team metric profiles for", year, "phase", phase)


if __name__ == "__main__":
    main()
