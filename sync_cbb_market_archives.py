#!/usr/bin/env python3
"""Capture actual pre-tipoff CBB odds and publish verified 2026-27 team ATS/O-U records.

An ESPN quote first observed after scheduled tipoff is NEVER used as a result line.
This supplements existing historical market archives without rewriting older seasons.
"""
import json
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SEASON = 2027
LEDGER = ROOT / "data/cbb/pregame-markets/2027.json"
MARKETS = ROOT / "data/cbb/markets"
TEAMS = ROOT / "data/cbb/teams"
URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?groups=50&limit=1000&dates="

def timestamp(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def number(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

def capture_event(e, now):
    if str(e.get("season", {}).get("year")) != str(SEASON):
        return None
    tip = timestamp(e["date"])
    if now >= tip or e.get("status", {}).get("type", {}).get("completed"):
        return None
    comps = e.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    sides = {v.get("homeAway"): v for v in comp.get("competitors", [])}
    if set(sides) != {"home", "away"}:
        return None
    odds = comp.get("odds") or []
    if not odds:
        return None
    q = odds[0]
    magnitude = number(q.get("spread"))
    home_fav = q.get("homeTeamOdds", {}).get("favorite")
    away_fav = q.get("awayTeamOdds", {}).get("favorite")
    home_spread = None
    if magnitude == 0:
        home_spread = 0.0
    elif magnitude is not None and home_fav is True and away_fav is not True:
        home_spread = -abs(magnitude)
    elif magnitude is not None and away_fav is True and home_fav is not True:
        home_spread = abs(magnitude)
    total = number(q.get("overUnder"))
    if home_spread is None and total is None:
        return None
    return {
        "id": str(e["id"]), "tipoff": e["date"], "observed_at": now.isoformat(),
        "home": str(sides["home"]["team"]["id"]), "away": str(sides["away"]["team"]["id"]),
        "home_spread": home_spread, "total": total,
        "provider": q.get("provider", {}).get("name"),
        "source": URL + tip.astimezone(ZoneInfo("America/New_York")).strftime("%Y%m%d"),
        "line_type": "ESPN pregame observed; not verified closing line",
    }

def update(now=None, fetch=None):
    now = now or datetime.now(timezone.utc)
    def load(url):
        req = urllib.request.Request(url, headers={"User-Agent": "BetWiseCBBMarkets/1.0"})
        with urllib.request.urlopen(req, timeout=35) as response:
            return json.load(response)
    fetch = fetch or load
    old = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"season": SEASON, "games": {}}
    if int(old["season"]) != SEASON:
        raise ValueError("Wrong market ledger season")
    entries = old.setdefault("games", {})
    day = now.astimezone(ZoneInfo("America/New_York")).date()
    observed = 0
    for offset in range(8):
        board = fetch(URL + (day + timedelta(days=offset)).strftime("%Y%m%d"))
        for e in board.get("events", []):
            row = capture_event(e, now)
            if row:
                prev = entries.get(row["id"])
                if prev:
                    # Preserve a previously verified side when a later quote omits it.
                    for field in ("home_spread", "total"):
                        if row[field] is None:
                            row[field] = prev.get(field)
                entries[row["id"]] = row
                observed += 1
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    new_ledger = {"season": SEASON, "last_checked": now.isoformat(), "games": entries}
    LEDGER.write_text(json.dumps(new_ledger, separators=(",", ":")) + "\n")
    count = 0
    for path in sorted(TEAMS.glob("*.json")):
        team = json.loads(path.read_text())
        current = team.get("seasons", {}).get(str(SEASON), {})
        completed = current.get("phases", {}).get("regular", {}).get("games", [])
        completed += current.get("phases", {}).get("postseason", {}).get("games", [])
        previous_path = MARKETS / path.name
        archive = json.loads(previous_path.read_text()) if previous_path.exists() else {"seasons": {}, "games": {}}
        games = {}
        ats = [0, 0, 0]
        ou = [0, 0, 0]
        for game in completed:
            if game.get("status") != "final":
                continue
            odds = entries.get(str(game["id"]))
            if not odds or timestamp(odds["observed_at"]) >= timestamp(odds["tipoff"]):
                continue
            pts, opp = number(game.get("points")), number(game.get("opponent_points"))
            if pts is None or opp is None:
                continue
            side = "home" if odds["home"] == str(team["team_id"]) else "away" if odds["away"] == str(team["team_id"]) else None
            if side is None:
                continue
            result = {"observed_at": odds["observed_at"], "source": odds["source"], "provider": odds.get("provider"), "line_type": odds["line_type"]}
            if odds.get("home_spread") is not None:
                spread = odds["home_spread"] if side == "home" else -odds["home_spread"]
                diff = pts - opp + spread
                outcome = "W" if diff > 0 else "L" if diff < 0 else "P"
                result.update(spread=spread, ats=outcome)
                ats[{"W": 0, "L": 1, "P": 2}[outcome]] += 1
            if odds.get("total") is not None:
                diff = pts + opp - odds["total"]
                outcome = "O" if diff > 0 else "U" if diff < 0 else "P"
                result.update(total=odds["total"], ou=outcome)
                ou[{"O": 0, "U": 1, "P": 2}[outcome]] += 1
            if "ats" in result or "ou" in result:
                games[str(game["id"])] = result
        if games or str(SEASON) in archive.get("games", {}):
            archive.setdefault("games", {})[str(SEASON)] = games
            archive.setdefault("seasons", {})[str(SEASON)] = {
                "ats": ats, "ou": ou, "source": "ESPN pregame observed lines",
                "coverage": "Only lines captured before scheduled tipoff; unlined games excluded",
                "expected_games": len([g for g in completed if g.get("status") == "final"]),
            }
            previous_path.parent.mkdir(parents=True, exist_ok=True)
            previous_path.write_text(json.dumps(archive, separators=(",", ":")) + "\n")
            count += 1
    print(json.dumps({"observed_upcoming_games": observed, "pregame_ledger_games": len(entries), "updated_team_market_files": count}))
    return new_ledger

if __name__ == "__main__":
    update()
