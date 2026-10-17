#!/usr/bin/env python3
"""Refresh only observed ESPN pregame market/status/probable fields.
Never recompute completed-game statistics, player production, or rankings.
"""
import json
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPORTS = {
    "nba": ("basketball/nba", "nba/dashboard/data/dashboard.json"),
    "mlb": ("baseball/mlb", "mlb/dashboard/data/dashboard.json"),
    "cbb": ("basketball/mens-college-basketball", "cbb/dashboard/data/dashboard.json"),
}

def request(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=25) as response:
                return json.load(response)
        except Exception:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)

def refresh(sport, route, destination):
    path = ROOT / destination
    data = json.loads(path.read_text())
    games = data.get("games", [])
    if not games:
        print(sport + ": no existing games; leaving published data intact")
        return
    now = datetime.now(timezone.utc)
    observed = now.isoformat()
    events = {}
    for offset in range(0, 8):
        day = (now + timedelta(days=offset)).strftime("%Y%m%d")
        url = "https://site.api.espn.com/apis/site/v2/sports/" + route + "/scoreboard?dates=" + day
        for event in request(url).get("events", []):
            events[str(event["id"])] = event
    updated = 0
    for game in games:
        event = events.get(str(game.get("id")))
        if not event or event.get("status", {}).get("type", {}).get("completed"):
            continue
        comp = (event.get("competitions") or [{}])[0]
        game["status"] = event.get("status", {}).get("type", {}).get("description", game.get("status"))
        quotes = comp.get("odds") or []
        if quotes:
            quote = quotes[0]
            game["market"] = {
                "spread": quote.get("details"),
                "total": quote.get("overUnder"),
                "provider": quote.get("provider", {}).get("name"),
                "observed_at": observed,
            }
        else:
            # Do not retain a stale market as if it were freshly observed.
            game["market"] = {"spread": None, "total": None, "provider": None, "observed_at": None}
        if sport == "mlb":
            sides = {c.get("homeAway"): c for c in comp.get("competitors", [])}
            for side in ("home", "away"):
                team_ref = game.get(side)
                team = team_ref if isinstance(team_ref, dict) else data.get("teams", {}).get(str(team_ref))
                if isinstance(team, dict):
                    team["probable"] = next(
                        (x.get("athlete", {}).get("displayName") for x in sides.get(side, {}).get("probables", []) if x.get("athlete")),
                        None,
                    )
        updated += 1
    if not updated:
        print(sport + ": no matching upcoming events; preserving existing snapshot")
        return
    data["pregame_updated_at"] = observed
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(sport + ": refreshed observed pregame fields for " + str(updated) + " games")

if __name__ == "__main__":
    for key, (route, dest) in SPORTS.items():
        refresh(key, route, dest)
