#!/usr/bin/env python3
"""Add CFBD play-mix rates to the dashboard without changing strength models."""
import json
import math
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "cfb-dashboard-preview/data/dashboard.json"
METRICS = (
    ("Rush Rate", "Rush Rate Against", "rush_rate", "rush_rate_against"),
    ("Pass Rate", "Pass Rate Against", "pass_rate", "pass_rate_against"),
)
ALIASES = {"UConn": "Connecticut", "Ole Miss": "Mississippi",
           "UTSA": "Texas-San Antonio", "Appalachian State": "App State",
           "FIU": "Florida International", "San Jose State": "San José State"}

def canon(name):
    return ALIASES.get(str(name), str(name)).casefold()

def request(path, **params):
    url = "https://api.collegefootballdata.com" + path + "?" + urllib.parse.urlencode(params)
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                "Authorization": "Bearer " + os.environ["CFBD_API_KEY"],
                "Accept": "application/json", "User-Agent": "BetWiseDashboard/1.0"})
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.load(response)
            if not isinstance(data, list):
                raise ValueError("Expected a CFBD list response")
            return data
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))

def rates(unit):
    """Read provider rates only; never substitute success rates or missing zeros."""
    if not isinstance(unit, dict) or not isinstance(unit.get("plays"), (int, float)) or unit["plays"] <= 0:
        return None
    rush = (unit.get("rushingPlays") or {}).get("rate")
    passing = (unit.get("passingPlays") or {}).get("rate")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
           not math.isfinite(v) or not 0 <= v <= 1 for v in (rush, passing)):
        return None
    if abs(rush + passing - 1) > 0.001:
        return None
    return rush, passing

def board(rows, season):
    result = {}
    for row in rows:
        if int(row.get("season", 0)) != season:
            continue
        offense, defense = rates(row.get("offense")), rates(row.get("defense"))
        if not row.get("team") or offense is None or defense is None:
            continue
        result[canon(row["team"])] = dict(zip(
            ("rush_rate", "pass_rate", "rush_rate_against", "pass_rate_against"),
            offense + defense))
    return result

def rank_board(teams):
    # Descriptive frequency rank: highest share is #1, including defense.
    for key in ("rush_rate", "pass_rate", "rush_rate_against", "pass_rate_against"):
        values = sorted((round(t[key], 12), name) for name, t in teams.items())
        values.reverse()
        previous, current = None, None
        for position, (value, name) in enumerate(values, 1):
            if value != previous:
                current = position
            teams[name][key + "_rank"] = current
            previous = value

def enrich(payload):
    games = payload.get("games") or []
    if not games:
        raise ValueError("Refusing to publish an empty dashboard")
    # Use only weeks preceding each matchup; no future/own-game statistics.
    windows = sorted({(int(g["season"]), int(g["week"]) - 1) for g in games})
    boards, metadata = {}, []
    for year, end_week in windows:
        if end_week < 1:
            boards[(year, end_week)] = {}
            continue
        params = dict(year=year, classification="fbs", excludeGarbageTime="true", endWeek=end_week)
        data = board(request("/stats/season/advanced", **params), year)
        if len(data) < 120:
            raise ValueError(f"Incomplete FBS play-rate source: {len(data)} teams")
        rank_board(data)
        names = {canon(g[s]["name"]) for g in games
                 if int(g["season"]) == year and int(g["week"]) - 1 == end_week
                 for s in ("away", "home")}
        missing = names - data.keys()
        if missing:
            # Some FBS fixtures involve FCS opponents. Their rates have no FBS rank.
            data.update({k: v for k, v in board(request("/stats/season/advanced",
                **dict(params, classification="fcs")), year).items() if k in missing})
        boards[(year, end_week)] = data
        metadata.append(dict(season=year, through_week=end_week,
                             fbs_ranked_teams=sum("rush_rate_rank" in v for v in data.values())))
    missing = set()
    for game in games:
        data = boards[(int(game["season"]), int(game["week"]) - 1)]
        for side in ("away", "home"):
            team = game[side]
            values = data.get(canon(team["name"]), {})
            if not values:
                missing.add(team["name"])
            raw = team.setdefault("raw_metrics", {})
            for _, _, off, deff in METRICS:
                for key in (off, deff):
                    raw[key] = values.get(key)
                    raw[key + "_rank"] = values.get(key + "_rank")
        labels = {m[0] for m in METRICS}
        rows = [r for r in game.get("matchup_metrics", []) if r["label"] not in labels]
        for off_label, def_label, off, deff in METRICS:
            row = dict(label=off_label, offense_label=off_label,
                       defense_label=def_label, format="percent", ranking_type="frequency")
            for side in ("away", "home"):
                raw = game[side]["raw_metrics"]
                for kind, key in (("offense", off), ("defense", deff)):
                    row[side + "_" + kind] = raw.get(key)
                    row[side + "_" + kind + "_rank"] = raw.get(key + "_rank")
            rows.append(row)
        game["matchup_metrics"] = rows
    payload.setdefault("slate", {})["play_mix"] = {
        "source": "CollegeFootballData /stats/season/advanced",
        "method": "Provider rushingPlays.rate and passingPlays.rate on offense and defense; garbage time excluded",
        "ranking": "Descending frequency among FBS teams; #1 means highest share, not best",
        "windows": metadata, "unavailable_teams": sorted(missing),
        "generated_at": datetime.now(timezone.utc).isoformat()}
    return payload

def main():
    payload = enrich(json.loads(OUT.read_text(encoding="utf-8")))
    OUT.write_text(json.dumps(payload, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload["slate"]["play_mix"], indent=2))
    print(f"Updated play-mix metrics in {len(payload['games'])} matchups")

if __name__ == "__main__":
    main()
