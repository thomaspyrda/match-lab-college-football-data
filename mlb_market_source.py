"""Independent MLB historical market observations and derived records."""
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parent


def load_markets(path, year, phase, now):
    try:
        doc = json.loads(path.read_text())
        age = now - datetime.fromisoformat(doc["collected_at"])
        if doc["season"] != year or doc["phase"] != phase or len(doc["teams"]) != 30 or not -timedelta(minutes=5) <= age <= timedelta(hours=30):
            return {}, {}
        return doc["quotes"], doc["teams"]
    except (OSError, ValueError, KeyError, TypeError):
        return {}, {}


def main():
    from zoneinfo import ZoneInfo
    from refresh_mlb_dashboard import season_market_records
    now = datetime.now(timezone.utc)
    year = now.astimezone(ZoneInfo("America/New_York")).year
    contexts = [json.loads(p.read_text()) for p in (ROOT / "mlb/pipeline").glob(f"team-metrics-{year}-*.json")]
    if not contexts:
        raise ValueError("No verified current MLB phase")
    phase = max(contexts, key=lambda d:d["collected_at"])["phase"]
    registry = json.loads((ROOT / "data/sports/team-registry.json").read_text())
    ids = {str(t["espn_id"]) for t in registry["teams"] if t["sport"] == "mlb"}
    if len(ids) != 30:
        raise ValueError("Expected 30 MLB teams")
    records = season_market_records(year, phase, now, ids)
    cache = ROOT / f"mlb/dashboard/data/season-market-cache-{year}-{phase}.json"
    quotes = json.loads(cache.read_text())
    path = ROOT / "mlb/pipeline/markets.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"season": year, "phase": phase, "collected_at": now.isoformat(), "quotes": quotes, "teams": records}, allow_nan=False, separators=(",", ":")) + "\n")
    temporary.replace(path)
    print("Collected historical market records for 30 MLB teams; quoted games:", len(quotes))


if __name__ == "__main__":
    main()
