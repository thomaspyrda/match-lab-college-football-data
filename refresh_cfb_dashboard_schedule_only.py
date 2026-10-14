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

def to_number(value):
    try:
        return float(value) if value is not None and str(value).strip() else None
    except (ValueError, TypeError):
        return None

def choose_market(game):
    # CFBD /lines is a current odds snapshot, NOT a guaranteed opening-line archive.
    offers = game.get("lines") or []
    preferred = ("consensus", "draftkings", "fanduel", "betmgm", "caesars", "espn bet", "bovada")
    offers = sorted(offers, key=lambda x: next((i for i, p in enumerate(preferred) if p in str(x.get("provider") or "").lower()), len(preferred)))
    for offer in offers:
        spread = to_number(offer.get("spread"))
        total = to_number(offer.get("overUnder"))
        if spread is not None or total is not None:
            return {"spread": spread, "total": total, "home_moneyline": to_number(offer.get("homeMoneyline")),
                    "away_moneyline": to_number(offer.get("awayMoneyline")), "provider": offer.get("provider"),
                    "line_type": "available", "formatted_spread": offer.get("formattedSpread")}
    return None

METRIC_PAIRS = [
    ("Sack Rate Allowed", "Sack Rate", "sack_rate_allowed", "sack_rate", "percent"),
    ("Havoc Allowed", "Havoc", "havoc_allowed", "havoc", "percent"),
    ("Turnovers", "Turnovers Forced", "turnovers", "turnovers_forced", "count"),
    ("Success Rate", "Defensive Success Rate", "overall_success", "defensive_success", "percent"),
    ("EPA / Play", "EPA / Play Allowed", "offensive_efficiency", "defensive_efficiency", "decimal"),
    ("Passing Success Rate", "Defensive Pass Success Rate", "passing_success", "defensive_passing_success", "percent"),
    ("Rushing Success Rate", "Defensive Rush Success Rate", "rushing_success", "defensive_rushing_success", "percent"),
    ("Explosiveness", "Explosiveness Allowed", "explosiveness", "defensive_explosiveness", "decimal"),
    ("Points per Opportunity", "Points per Opportunity Allowed", "finishing_drives", "defensive_finishing_drives", "decimal"),
    ("Third Down Conversion", "Third Down Defense", "third_down_conversion", "defensive_third_down_conversion", "percent"),
    ("Red Zone TD Rate", "Red Zone TD Defense", "red_zone_td_rate", "defensive_red_zone_td_rate", "percent"),
]

def build_metric_rows(away, home):
    def val(team, key):
        return ((team.get("advanced") or {}).get("raw") or {}).get(key)
    def rank(team, key):
        return (team.get("advanced") or {}).get(key)
    rows = []
    for label, defense_label, off, de, fmt in METRIC_PAIRS:
        rows.append({"label": label, "offense_label": label, "defense_label": defense_label, "format": fmt,
                     "away_offense": val(away, off), "home_defense": val(home, de),
                     "home_offense": val(home, off), "away_defense": val(away, de),
                     "away_offense_rank": rank(away, off), "home_defense_rank": rank(home, de),
                     "home_offense_rank": rank(home, off), "away_defense_rank": rank(away, de)})
    return rows

def build_factors(away, home, rows, conference_game=False, neutral_site=False):
    edges = []
    for row in rows:
        for off_side, def_side in (("away", "home"), ("home", "away")):
            off_rank = row.get(off_side + "_offense_rank")
            def_rank = row.get(def_side + "_defense_rank")
            if isinstance(off_rank, int) and isinstance(def_rank, int):
                gap = abs(off_rank - def_rank)
                if gap >= 12:
                    edge_side = off_side if off_rank < def_rank else def_side
                    edges.append((gap, {"type": "matchup_edge", "metric": row["label"],
                                        "team": away["name"] if edge_side == "away" else home["name"],
                                        "edge_unit": "offense" if off_rank < def_rank else "defense",
                                        "offense_side": off_side, "direction": "rank gap", "gap": gap}))
    factors = [item for _, item in sorted(edges, key=lambda entry: entry[0], reverse=True)[:5]]
    if conference_game:
        factors.append({"type": "game_context", "detail": "conference matchup"})
    if neutral_site:
        factors.append({"type": "game_context", "detail": "neutral-site matchup"})
    return factors[:8]

def player_placeholders(team):
    slots = [("QB", "Projected starting QB"), ("RB", "Top usage RB"),
             ("WR", "Top usage WR"), ("TE", "Top usage TE"),
             ("Skill", "Next skill player")]
    return [{"team": team.get("abbr") or team["name"], "name": "Player data pending",
             "position": pos, "usage": [], "placeholder": True, "slot": slot} for pos, slot in slots]

def rest_days(team, kickoff, all_fixtures):
    last = None
    for game in all_fixtures:
        game_date = parse_date(game.get("startDate"))
        if not game_date or not game_date < kickoff:
            continue
        if canon(team) not in (canon(game.get("homeTeam")), canon(game.get("awayTeam"))):
            continue
        if game.get("homePoints") is None or game.get("awayPoints") is None:
            continue
        if last is None or game_date > last:
            last = game_date
    if last is None:
        return None
    return (kickoff.astimezone(ET).date() - last.astimezone(ET).date()).days

def main():
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=7)
    existing = json.loads(OUT.read_text(encoding="utf-8"))
    old_games = existing.get("games", [])
    by_id = {str(x.get("game_id")): x for x in old_games}
    known_players = {}
    for old in old_games:
        cards = old.get("players") or []
        if len(cards) >= 10:
            for side, subset in (("away", cards[:5]), ("home", cards[5:10])):
                identity = (old.get(side) or {}).get("name")
                if identity and any(not p.get("placeholder") for p in subset):
                    known_players[canon(identity)] = subset
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
    season_games = []
    for week in range(1, 18):
        rows = request("/games", year=year, seasonType="regular", week=week)
        season_games.extend(rows)
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

    # Reuse source advanced statistics without recomputing or editing any rankings.
    upcoming_path = ROOT / "data/upcoming.json"
    source_games = json.loads(upcoming_path.read_text(encoding="utf-8")).get("games", []) if upcoming_path.exists() else []
    source_by_id = {str(g.get("game_id")): g for g in source_games}
    advanced_by_team = {}
    for sg in source_games:
        for side in ("away", "home"):
            team_name = sg.get(side)
            profile = sg.get(side + "_profile") or {}
            if team_name and profile.get("advanced"):
                advanced_by_team[canon(team_name)] = profile

    # Fetch CFBD market snapshots for only the weeks represented in the seven-day slate.
    market_by_id = {}
    successful_line_weeks = set()
    for week in sorted({int(g.get("week") or 0) for g in fixtures.values()}):
        if week < 1:
            continue
        try:
            offers = request("/lines", year=year, seasonType="regular", week=week)
            successful_line_weeks.add(week)
        except Exception as exc:
            print(f"Lines unavailable for week {week}: {exc}; leaving existing market unchanged")
            continue
        for game in offers:
            market = choose_market(game)
            if market:
                market_by_id[str(game.get("id"))] = market
    print(f"CFBD available odds for {len(market_by_id)} of {len(fixtures)} upcoming games")


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
        # Refresh current available spread and O/U; do not invent prices or claim opening lines.
        if game_id in market_by_id:
            row["market"] = {**(row.get("market") or {}), **market_by_id[game_id]}
        elif int(g.get("week") or 0) in successful_line_weeks:
            row["market"] = {"spread": None, "total": None, "home_moneyline": None, "away_moneyline": None, "provider": None, "line_type": "unavailable"}
        elif not cached:
            row["market"]["line_type"] = "unavailable"
        # Every matchup gets the full comparison grid, with missing stats clearly unavailable.
        source = source_by_id.get(game_id) or {}
        away_profile = (source.get("away_profile") or advanced_by_team.get(canon(g["awayTeam"])) or {})
        home_profile = (source.get("home_profile") or advanced_by_team.get(canon(g["homeTeam"])) or {})
        if not row.get("matchup_metrics"):
            row["matchup_metrics"] = build_metric_rows(away_profile, home_profile)
        elif not any(m.get("away_offense") is not None or m.get("home_defense") is not None
                     for m in row["matchup_metrics"]):
            row["matchup_metrics"] = build_metric_rows(away_profile, home_profile)
        # Restore complete detail-section structures for newly added schedule games.
        if not row.get("trends"):
            row["trends"] = build_factors(row["away"], row["home"], row["matchup_metrics"],
                                           g.get("conferenceGame"), g.get("neutralSite"))
        if not row.get("players") or all(p.get("placeholder") for p in row["players"]):
            row["players"] = (known_players.get(canon(g["awayTeam"])) or player_placeholders(row["away"])) + (known_players.get(canon(g["homeTeam"])) or player_placeholders(row["home"]))
        start = parse_date(g.get("startDate"))
        row["rest_days"] = {
            "away": rest_days(g["awayTeam"], start, season_games),
            "home": rest_days(g["homeTeam"], start, season_games),
        } if start else {"away": None, "home": None}
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
