#!/usr/bin/env python3
"""Build pregame-only advanced team profiles and weekly FBS percentiles."""
import json, os, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = DATA / "profiles"
OUT.mkdir(parents=True, exist_ok=True)
KEY = os.environ.get("CFBD_API_KEY")
if not KEY:
    raise SystemExit("CFBD_API_KEY secret is required")

METRICS = {
    "offensive_efficiency": ("offense", "ppa", True),
    "defensive_efficiency": ("defense", "ppa", False),
    "rushing_success": ("offense", "rushingPlays", "successRate", True),
    "passing_success": ("offense", "passingPlays", "successRate", True),
    "explosiveness": ("offense", "explosiveness", True),
    "havoc": ("defense", "havoc", "total", True),
    "finishing_drives": ("offense", "pointsPerOpportunity", True),
}

def api(path, **params):
    url = "https://api.collegefootballdata.com" + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + KEY, "Accept": "application/json", "User-Agent": "MatchLab/1.0"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                return json.load(response)
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)

def value(row, spec):
    cur = row
    for key in spec[:-1]:
        cur = cur.get(key) if isinstance(cur, dict) else None
    try:
        return float(cur) if cur is not None else None
    except (TypeError, ValueError):
        return None

def midpoint_percentile(v, values, higher):
    usable = [x for x in values if x is not None]
    if v is None or len(usable) < 2:
        return None
    worse = sum(x < v for x in usable) if higher else sum(x > v for x in usable)
    tied = sum(x == v for x in usable)
    pct = 100 * (worse + (tied - 1) / 2) / (len(usable) - 1)
    return max(1, min(100, int(pct + 0.5)))

def prior_game_counts(year):
    path = DATA / "historical" / f"{year}.json"
    if not path.exists():
        return {}
    games = json.loads(path.read_text(encoding="utf-8")).get("games", [])
    counts = defaultdict(lambda: defaultdict(int))
    teams = set()
    for game in games:
        teams.update((game.get("home"), game.get("away")))
    for week in range(1, 22):
        for team in teams:
            counts[week][team] = sum(1 for g in games if g.get("result") and g.get("week", 0) < week and team in (g.get("home"), g.get("away")))
    return counts

def build_year(year, weeks):
    counts = prior_game_counts(year)
    output = {}
    for week in weeks:
        if week <= 1:
            output[str(week)] = {"through_week": 0, "teams": {}}
            continue
        rows = api("/stats/season/advanced", year=year, endWeek=week - 1, classification="fbs", excludeGarbageTime="true")
        raw = {}
        for row in rows:
            team = row.get("team")
            if not team:
                continue
            raw[team] = {name: value(row, spec[:-1]) for name, spec in METRICS.items()}
        boards = {name: [team_values.get(name) for team_values in raw.values()] for name in METRICS}
        teams = {}
        for team, team_values in raw.items():
            scores = {}
            for name, spec in METRICS.items():
                scores[name] = midpoint_percentile(team_values[name], boards[name], spec[-1])
            scores["games_played"] = counts.get(week, {}).get(team, 0)
            scores["metrics_available"] = sum(v is not None for k, v in scores.items() if k not in ("games_played", "metrics_available"))
            teams[team] = scores
        output[str(week)] = {"through_week": week - 1, "fbs_field_size": len(raw), "teams": teams}
        print(f"{year} week {week}: {len(raw)} FBS advanced profiles")
    payload = {"schema_version": "2.0", "season": year, "pregame_only": True, "generated_at": datetime.now(timezone.utc).isoformat(), "weeks": output}
    temp = OUT / f".{year}.tmp"
    temp.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    temp.replace(OUT / f"{year}.json")

def main():
    current = datetime.now(timezone.utc).year
    for weekly_file in sorted((DATA / "weekly").glob("*.json")):
        weekly = json.loads(weekly_file.read_text(encoding="utf-8"))
        year = int(weekly["season"])
        target = OUT / f"{year}.json"
        if year < current and target.exists():
            print(f"{year}: using validated cached profiles")
            continue
        weeks = sorted(int(w) for w in weekly.get("weeks", {}))
        if year == current:
            history_path = DATA / "historical" / f"{year}.json"
            games = json.loads(history_path.read_text(encoding="utf-8")).get("games", []) if history_path.exists() else []
            last_completed = max((int(g.get("week") or 0) for g in games if g.get("result")), default=0)
            weeks = [w for w in weeks if w <= last_completed + 2]
        build_year(year, weeks)

if __name__ == "__main__":
    main()
