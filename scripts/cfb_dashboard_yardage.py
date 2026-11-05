"""Add dashboard yardage pairs from the existing verified CFB metrics snapshot."""
import argparse
import json
import math
from pathlib import Path

ALIASES = {"UConn": "Connecticut", "Ole Miss": "Mississippi", "UTSA": "Texas-San Antonio",
           "Appalachian State": "App State", "FIU": "Florida International",
           "San Jose State": "San José State", "Miami (FL)": "Miami", "Hawaii": "Hawai'i",
           "UMass": "Massachusetts", "Louisiana-Lafayette": "Louisiana"}
METRICS = [
    ("Pass Yards/Game", "Pass Yards Allowed/Game", "pass_yards_per_game", "yardage"),
    ("Yards/Completion", "Yards Allowed/Completion", "yards_per_completion", "average"),
    ("Rush Yards/Game", "Rush Yards Allowed/Game", "rush_yards_per_game", "yardage"),
    ("Yards/Carry", "Yards/Carry Allowed", "yards_per_carry", "average"),
    ("Line Yards", "Line Yards Allowed", "line_yards", "average"),
]


def canon(name):
    return ALIASES.get(str(name), str(name)).casefold()


def number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def ratio(value, denominator):
    return value / denominator if value is not None and denominator is not None and denominator > 0 else None


def board(snapshot):
    source = snapshot["payload"]
    season = int(snapshot["season"])
    basic = {}
    for row in source["basic"]:
        if int(row.get("season") or 0) != season:
            continue
        name, key = canon(row["team"]), row["statName"]
        value = number(row.get("statValue"))
        stats = basic.setdefault(name, {})
        if key in stats and stats[key] != value:
            raise ValueError("Conflicting CFB team stat: " + name + " " + key)
        stats[key] = value
    advanced = {canon(r["team"]): r for r in source["advanced"] if int(r.get("season") or 0) == season}
    # The existing collector's dashboard team set is the established FBS rank universe.
    fbs = {canon(name) for name in source["dashboard"]["teams"]}
    teams = {}
    for name in basic.keys() | advanced.keys():
        stats, adv = basic.get(name, {}), advanced.get(name, {})
        values = {}
        for phase, suffix in (("offense", ""), ("defense", "Opponent")):
            passing = stats.get("netPassingYards" + suffix)
            rushing = stats.get("rushingYards" + suffix)
            games = stats.get("games")
            values[phase] = {
                "pass_yards_per_game": ratio(passing, games),
                "yards_per_completion": ratio(passing, stats.get("passCompletions" + suffix)),
                "rush_yards_per_game": ratio(rushing, games),
                "yards_per_carry": ratio(rushing, stats.get("rushingAttempts" + suffix)),
                "line_yards": number((adv.get(phase) or {}).get("lineYards")),
            }
        teams[name] = values
    for phase in ("offense", "defense"):
        for _, _, key, _ in METRICS:
            eligible = [v[phase][key] for name, v in teams.items()
                        if name in fbs and v[phase][key] is not None]
            for name, values in teams.items():
                value = values[phase][key]
                values[phase][key + "_rank"] = (1 + sum(
                    other > value if phase == "offense" else other < value for other in eligible
                )) if name in fbs and value is not None else None
    return teams


def enrich(payload, snapshot):
    teams = board(snapshot)
    labels = {m[0] for m in METRICS}
    for game in payload["games"]:
        if int(game["season"]) != int(snapshot["season"]):
            raise ValueError("CFB yardage snapshot season mismatch")
        rows = [r for r in game["matchup_metrics"] if r["label"] not in labels]
        for off_label, def_label, key, fmt in METRICS:
            row = dict(label=off_label, offense_label=off_label, defense_label=def_label, format=fmt)
            for side in ("away", "home"):
                raw = game[side].setdefault("raw_metrics", {})
                values = teams.get(canon(game[side]["name"]), {})
                for phase in ("offense", "defense"):
                    value = values.get(phase, {}).get(key)
                    rank = values.get(phase, {}).get(key + "_rank")
                    row[side + "_" + phase] = value
                    row[side + "_" + phase + "_rank"] = rank
                    raw[phase + "_" + key] = value
                    raw[phase + "_" + key + "_rank"] = rank
            rows.append(row)
        game["matchup_metrics"] = rows
    payload.setdefault("slate", {})["yardage"] = {
        "source": "CollegeFootballData verified metrics snapshot",
        "collected_at": snapshot["collected_at"],
        "through_week": snapshot.get("through_week"),
        "method": "Season team yardage totals / games, completions or carries; provider Line Yards per rush excludes garbage time.",
        "rank": "Higher offense and lower defense rank first among the existing FBS team universe.",
    }
    return payload


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--dashboard", type=Path, default=root / "cfb-dashboard-preview/data/dashboard.json")
    parser.add_argument("--snapshot", type=Path, default=root / "data/cfb/pipeline/metrics.json")
    args = parser.parse_args()
    payload = enrich(json.loads(args.dashboard.read_text()), json.loads(args.snapshot.read_text()))
    if not payload.get("games"):
        raise ValueError("Refusing to publish an empty dashboard")
    args.dashboard.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")
    print("Published yardage pairs for", len(payload["games"]), "CFB matchups")


if __name__ == "__main__":
    main()
