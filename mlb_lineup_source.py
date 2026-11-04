"""Independent MLB confirmed-lineup and probable-starter observations."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def signature(event):
    return {"date": event["date"], "teams": sorted(c["team"]["id"] for c in event["competitions"][0]["competitors"])}


def load_context(path, year, phase, upcoming, now):
    empty = ({}, {}, {})
    try:
        doc = json.loads(path.read_text())
        age = now - datetime.fromisoformat(doc["collected_at"])
        if doc["season"] != year or doc["phase"] != phase or not -timedelta(minutes=5) <= age <= timedelta(hours=6):
            return empty
        accepted = {str(e["id"]) for e in upcoming if doc["events"].get(str(e["id"])) == signature(e)}
        lineups = {gid: rows for gid, rows in doc["lineups"].items() if gid in accepted}
        # Probable starters apply only to event dates/teams present in this exact slate.
        from zoneinfo import ZoneInfo
        dates = {datetime.fromisoformat(e["date"].replace("Z", "+00:00")).astimezone(ZoneInfo("America/New_York")).date().isoformat() for e in upcoming if str(e["id"]) in accepted}
        starters = {(day, name): player for day, name, player in doc["starters"] if day in dates} if len(accepted) == len(upcoming) else {}
        return lineups, doc["recent_lineups"], starters
    except (OSError, ValueError, KeyError, TypeError):
        return empty


def main():
    from concurrent.futures import ThreadPoolExecutor
    from zoneinfo import ZoneInfo
    from refresh_mlb_dashboard import get, stamp, game_lineups, official_probables
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("America/New_York")).date()
    year = today.year
    registry = json.loads((ROOT / "data/sports/team-registry.json").read_text())
    ids = {str(t["espn_id"]) for t in registry["teams"] if t["sport"] == "mlb"}
    if len(ids) != 30:
        raise ValueError("Expected 30 MLB teams")
    dates = [today + timedelta(days=i) for i in range(-8, 8)]
    with ThreadPoolExecutor(8) as pool:
        boards = list(pool.map(lambda d: get("scoreboard?limit=1000&dates=" + d.strftime("%Y%m%d")), dates))
    events = {str(e["id"]): e for b in boards for e in b.get("events", []) if all(c["team"]["id"] in ids for c in e["competitions"][0]["competitors"])}
    upcoming = sorted([e for e in events.values() if not e["status"]["type"].get("completed") and stamp(e["date"]) >= now-timedelta(hours=8)], key=lambda e:e["date"])
    phase = upcoming[0]["season"]["type"] if upcoming else (3 if today.month >= 10 else 2)
    upcoming = [e for e in upcoming if e["season"]["type"] == phase]
    past = sorted([e for e in events.values() if e["status"]["type"].get("completed") and e["season"]["type"] == phase and stamp(e["date"]) <= now], key=lambda e:e["date"], reverse=True)[:18]
    def one(e):
        return str(e["id"]), game_lineups(e["id"], {c["team"]["id"] for c in e["competitions"][0]["competitors"]})
    with ThreadPoolExecutor(6) as pool:
        lineups = dict(pool.map(one, upcoming))
    recent = {}
    with ThreadPoolExecutor(6) as pool:
        found = dict(pool.map(one, past))
    for event in past:
        for tid, players in found[str(event["id"])].items():
            recent.setdefault(tid, {"players": players, "date": event["date"]})
    starters = official_probables(upcoming)
    doc = {"season": year, "phase": phase, "collected_at": now.isoformat(), "events": {str(e["id"]):signature(e) for e in upcoming},
           "lineups": lineups, "recent_lineups": recent, "starters": [[day,name,player] for (day,name),player in starters.items()]}
    path = ROOT / "mlb/pipeline/lineups.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    temporary.replace(path)
    print("Collected lineup context for", len(upcoming), "upcoming MLB games")


if __name__ == "__main__":
    main()
