"""Independent MLB player statistics using the existing phase-specific calculations."""
import json
from datetime import datetime, timezone
from pathlib import Path
from mlb_metric_source import load_profiles

ROOT = Path(__file__).resolve().parent


def source_path(year, phase):
    return ROOT / f"mlb/pipeline/player-statistics-{year}-{phase}.json"


def load_player_stats(path, year, phase, required_ids, now):
    if not required_ids:
        return {}
    doc = json.loads(path.read_text())
    ids = set(doc.get("teams", {}))
    if len(ids) != 30 or not set(required_ids) <= ids:
        raise ValueError("Incomplete MLB player-stat population")
    return load_profiles(path, year, phase, ids, now)


def main():
    from zoneinfo import ZoneInfo
    from refresh_mlb_dashboard import current_phase_player_stats
    now = datetime.now(timezone.utc)
    year = now.astimezone(ZoneInfo("America/New_York")).year
    candidates = [json.loads(p.read_text()) for p in (ROOT / "mlb/pipeline").glob(f"team-metrics-{year}-*.json")]
    if not candidates:
        raise ValueError("No verified current MLB season phase")
    context = max(candidates, key=lambda d: d["collected_at"])
    phase = context["phase"]
    registry = json.loads((ROOT / "data/sports/team-registry.json").read_text())
    teams = {str(t["espn_id"]): t for t in registry["teams"] if t["sport"] == "mlb"}
    if len(teams) != 30:
        raise ValueError("Expected 30 registered MLB teams")
    statistics = current_phase_player_stats(teams, year, phase)
    if set(statistics) != set(teams) or not any(statistics.values()):
        raise ValueError("Incomplete or empty MLB player statistics")
    path = source_path(year, phase)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"season": year, "phase": phase, "collected_at": now.isoformat(), "teams": statistics}, allow_nan=False, separators=(",", ":")) + "\n")
    temporary.replace(path)
    print("Collected player statistics for", len(statistics), "teams in", year, "phase", phase)


if __name__ == "__main__":
    main()
