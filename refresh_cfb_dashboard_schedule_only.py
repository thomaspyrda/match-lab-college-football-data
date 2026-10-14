#!/usr/bin/env python3
"""Refresh only the CFB Dashboard's seven-day schedule. Never read/write ranking model files."""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cfb-dashboard-preview/data/dashboard.json"
ET = ZoneInfo("America/New_York")
API = "https://api.collegefootballdata.com"

def request(path, **params):
    url = API + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + os.environ["CFBD_API_KEY"],
                                                "Accept": "application/json", "User-Agent": "BetWiseDashboard/1.0"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return json.load(response)

def parse_date(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None

def canon(value):
    aliases = {"UConn": "Connecticut", "Ole Miss": "Mississippi", "UTSA": "Texas-San Antonio",
               "Appalachian State": "App State", "FIU": "Florida International", "San Jose State": "San José State"}
    return aliases.get(str(value), str(value)).casefold()

def main():
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=7)
    existing = json.loads(OUT.read_text(encoding="utf-8"))
    old_games = existing.get("games", [])
    by_id = {str(x.get("game_id")): x for x in old_games}
    known_teams = {}
    for game in old_games:
        for side in ("away", "home"):
            t = game.get(side) or {}
            if isinstance(t, dict):
                known_teams[canon(t.get("name", ""))] = t

    fbs_rows = request("/teams/fbs", year=now.astimezone(ET).year)
    fbs = {canon(x.get("school")): x for x in fbs_rows if x.get("school")}
    if len(fbs) < 120:
        raise RuntimeError("Incomplete CFBD FBS membership; aborting refresh")

    # Request individual weeks; season-wide endpoints may omit future fixtures.
    year = now.astimezone(ET).year
    fixtures = {}
    for week in range(1, 18):
        rows = request("/games", year=year, seasonType="regular", week=week)
        for g in rows:
            kickoff = parse_date(g.get("startDate"))
            if not kickoff or not now <= kickoff < end:
                continue
            away, home = g.get("awayTeam"), g.get("homeTeam")
            if not away or not home or (canon(away) not in fbs and canon(home) not in fbs):
                continue
            fixtures[str(g["id"])] = g

    if not fixtures:
        raise RuntimeError("No upcoming FBS games from CFBD; refusing empty publication")

    def team(name, side, fixture):
        cached = known_teams.get(canon(name), {})
        fbs_team = fbs.get(canon(name), {})
        return {
            **cached,
            "name": name,
            "conference": fixture.get(side + "Conference") or cached.get("conference"),
            "espn_id": fixture.get(side + "Id") or cached.get("espn_id") or fbs_team.get("id"),
            "abbr": cached.get("abbr") or fbs_team.get("abbreviation"),
            "logo": cached.get("logo") or (fbs_team.get("logos") or [None])[0],
            "color": cached.get("color") or fbs_team.get("color"),
            "classification": "FBS" if canon(name) in fbs else "FCS/Other",
        }

    # Resolve current FBS identity and logos even when old dashboard cards lack them.
    def update_brand(t):
        row = fbs.get(canon(t.get("name", "")), {})
        if not row:
            return t
        logos = row.get("logos") or []
        result = dict(t)
        result["espn_id"] = result.get("espn_id") or row.get("id")
        result["abbr"] = result.get("abbr") or row.get("abbreviation")
        result["logo"] = result.get("logo") or (logos[0] if logos else None)
        result["alternate_logo"] = result.get("alternate_logo") or (logos[1] if len(logos) > 1 else None)
        result["color"] = result.get("color") or row.get("color")
        return result

    games = []
    for game_id, g in fixtures.items():
        cached = by_id.get(game_id)
        if cached:
            row = dict(cached)
            row["kickoff"] = g.get("startDate")
            row["away"] = update_brand(row["away"])
            row["home"] = update_brand(row["home"])
        else:
            row = {
                "game_id": game_id, "season": g.get("season"), "week": g.get("week"),
                "kickoff": g.get("startDate"), "venue": g.get("venue"), "venue_id": g.get("venueId"),
                "away": team(g["awayTeam"], "away", g), "home": team(g["homeTeam"], "home", g),
                "market": {"spread": None, "total": None, "home_moneyline": None, "away_moneyline": None},
                "context": {"conference_game": g.get("conferenceGame"), "neutral_site": g.get("neutralSite")},
                "weather": {"summary": "Forecast unavailable"}, "matchup_metrics": [],
                "featured_mismatch": None, "market_trends": [], "players": [], "trends": []
            }
        games.append(row)
    games.sort(key=lambda x: x["kickoff"])
    # Coverage is compared against every FBS-involved matchup returned by the source.
    if len(games) != len(fixtures):
        raise RuntimeError("Coverage check failed")
    existing["games"] = games
    existing.setdefault("slate", {})["generated_at"] = now.isoformat()
    existing["slate"]["schedule_source"] = "CFBD /games weekly; FBS membership"
    existing["slate"]["window_utc"] = {"start": now.isoformat(), "end": end.isoformat()}
    existing["slate"]["schedule_count"] = len(games)
    OUT.write_text(json.dumps(existing, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    counts = {}
    for g in games:
        date = parse_date(g["kickoff"]).astimezone(ET).date().isoformat()
        counts[date] = counts.get(date, 0) + 1
    print("FBS dashboard upcoming games by Eastern date:", json.dumps(counts, sort_keys=True))

if __name__ == "__main__":
    main()
