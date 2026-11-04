"""Independent NBA matchup availability observations."""
import copy
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from nba_player_context import build_availability, stamp, ET

ROOT = Path(__file__).resolve().parent
PATH = ROOT / "nba/pipeline/availability.json"


def apply_saved(games, now, path):
    try:
        doc = json.loads(path.read_text())
        age = now - stamp(doc["collected_at"])
        if age < -timedelta(minutes=5) or age > timedelta(hours=18):
            raise ValueError("stale observation")
        saved = doc["games"]
    except (OSError, KeyError, ValueError, TypeError):
        saved = {}
    for game in games:
        fact = saved.get(str(game["id"]), {})
        for side in ("away", "home"):
            team = game[side]
            result = build_availability(team["id"], game["date"], now)
            observed = fact.get(side, {})
            report = observed.get("availability", {})
            if (fact.get("date") == game["date"] and observed.get("team_id") == str(team["id"])
                    and report.get("game_date") == now.astimezone(ET).date().isoformat()):
                try:
                    checked = now - stamp(report["checked_at"])
                    as_of = now - stamp(report["report_as_of"]) if report.get("report_as_of") else checked
                    if -timedelta(minutes=5) <= checked <= timedelta(hours=18) and -timedelta(minutes=5) <= as_of <= timedelta(hours=30):
                        result = copy.deepcopy(report)
                except (KeyError, ValueError, TypeError):
                    pass
            team["availability"] = result


def main():
    from nba_player_context import refresh_availability, API
    from refresh_nba_dashboard import get
    data = json.loads((ROOT / "nba/dashboard/data/dashboard.json").read_text())
    games = data["games"]
    now = datetime.now(timezone.utc)
    refresh_availability(games, now, lambda url: get(url[len(API):]))
    facts = {str(g["id"]): {"date": g["date"], **{side: {"team_id": str(g[side]["id"]),
              "availability": g[side]["availability"]} for side in ("away", "home")}} for g in games}
    PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps({"collected_at": now.isoformat(), "games": facts}, separators=(",", ":")) + "\n")
    temporary.replace(PATH)


if __name__ == "__main__":
    main()
