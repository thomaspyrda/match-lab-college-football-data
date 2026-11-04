"""Independent NBA roster collection, preserving each observation timestamp."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "nba/pipeline/rosters.json"


def load_rosters(path, season, team_ids):
    doc = json.loads(path.read_text())
    if doc.get("season") != season or set(doc.get("teams", {})) != set(team_ids):
        raise ValueError("Wrong season or incomplete NBA roster coverage")
    for tid, row in doc["teams"].items():
        if row.get("team_id") != tid or not row.get("players") or not row.get("observed_at"):
            raise ValueError("Invalid NBA roster observation")
    return doc["teams"]


def collect(team_ids, season, fetch, previous, now):
    retained = []
    def one(tid):
        try:
            row = fetch(tid)
            if row.get("team_id") != tid or not row.get("players") or not row.get("observed_at"):
                raise ValueError("Invalid roster")
            return tid, row
        except Exception as exc:
            if tid not in previous:
                raise ValueError("No verified roster fallback for " + tid) from exc
            retained.append(tid)
            return tid, previous[tid]
    with ThreadPoolExecutor(8) as pool:
        teams = dict(pool.map(one, team_ids))
    return {"season": season, "collected_at": now.isoformat(), "retained_teams": sorted(retained), "teams": teams}


def main():
    from refresh_nba_dashboard import roster
    from zoneinfo import ZoneInfo
    now = datetime.now(timezone.utc)
    local = now.astimezone(ZoneInfo("America/New_York"))
    season = local.year + (local.month >= 7)
    registry = json.loads((ROOT / "data/sports/team-registry.json").read_text())
    ids = [str(t["espn_id"]) for t in registry["teams"] if t["sport"] == "nba"]
    if len(ids) != 30 or len(set(ids)) != 30:
        raise ValueError("Expected 30 distinct NBA teams")
    previous = load_rosters(PATH, season, ids) if PATH.exists() and json.loads(PATH.read_text()).get("season") == season else {}
    doc = collect(ids, season, roster, previous, now)
    PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(PATH)
    print("Verified 30 rosters; retained previous observations for", len(doc["retained_teams"]), "teams")


if __name__ == "__main__":
    main()
