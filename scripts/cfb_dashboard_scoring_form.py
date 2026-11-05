"""Enrich CFB matchup scoring and last-five market records from saved verified inputs."""
import argparse
import json
import math
from datetime import datetime
from pathlib import Path

ALIASES = {"UConn": "Connecticut", "Ole Miss": "Mississippi", "UTSA": "Texas-San Antonio",
           "Appalachian State": "App State", "FIU": "Florida International",
           "San Jose State": "San José State", "Miami (FL)": "Miami",
           "Hawaii": "Hawai'i", "UMass": "Massachusetts", "Louisiana-Lafayette": "Louisiana"}


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


def stamp(value):
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def source_games(results):
    source = results["payload"]
    rows = list(source["team_games"])
    for key, response in source.get("responses", {}).items():
        if key.startswith("/games?"):
            rows.extend(response)
    games = {}
    for g in rows:
        if int(g.get("season") or results["season"]) != int(results["season"]):
            continue
        if g.get("seasonType", "regular") != "regular" or g.get("completed") is not True:
            continue
        scores = [number(g.get(side + "Points")) for side in ("home", "away")]
        if any(v is None or v < 0 for v in scores):
            continue
        games[str(g["id"])] = g
    return list(games.values())


def fbs_teams(results):
    response = results["payload"].get("responses", {})
    teams = {canon(t["school"]) for key, rows in response.items() if key.startswith("/teams/fbs?")
             for t in rows if t.get("school")}
    if not teams:
        teams = {canon(t) for t in results["payload"]["files"]["data/cfb_dashboard_team_metadata.json"]["teams"]}
    return teams


def quotes(markets):
    if not markets:
        return {}
    source = markets["payload"]
    rows = list(source.get("season_lines", []))
    for week in source.get("weeks", {}).values():
        rows.extend(week)
    out = {}
    for row in rows:
        available = [q for q in row.get("lines", []) if number(q.get("spread")) is not None
                     or number(q.get("overUnder")) is not None]
        quote = next((q for q in available if str(q.get("provider", "")).lower() == "consensus"),
                     available[0] if available else None)
        if quote:
            out[str(row["id"])] = quote
    return out


def enrich(payload, results, markets=None):
    if markets and int(markets["season"]) != int(results["season"]):
        raise ValueError("CFB markets season mismatch")
    games, fbs, lines = source_games(results), fbs_teams(results), quotes(markets)
    observed = stamp(results["collected_at"])
    for matchup in payload["games"]:
        if int(matchup["season"]) != int(results["season"]):
            raise ValueError("CFB scoring season mismatch")
        cutoff = min(stamp(matchup["kickoff"]), observed) if matchup.get("kickoff") else observed
        history = {}
        for g in games:
            if stamp(g["startDate"]) >= cutoff:
                continue
            for side, other in (("home", "away"), ("away", "home")):
                name = canon(g[side + "Team"])
                history.setdefault(name, []).append((g, side, other))
        summaries = {}
        for name, rows in history.items():
            summaries[name] = dict(ppg=sum(number(g[s + "Points"]) for g, s, _ in rows) / len(rows),
                                   allowed=sum(number(g[o + "Points"]) for g, _, o in rows) / len(rows))
        pair = dict(label="PPG", offense_label="PPG", defense_label="PPG Allowed", format="yardage")
        for side in ("away", "home"):
            team = matchup[side]
            name = canon(team["name"])
            values = summaries.get(name, {})
            for phase, key in (("offense", "ppg"), ("defense", "allowed")):
                value = values.get(key)
                eligible = [v[key] for n, v in summaries.items() if n in fbs]
                rank = (1 + sum(x > value if phase == "offense" else x < value for x in eligible)
                        ) if value is not None and name in fbs else None
                pair[side + "_" + phase] = value
                pair[side + "_" + phase + "_rank"] = rank
            recent = sorted(history.get(name, []), key=lambda row: row[0]["startDate"])[-5:]
            record = dict(ats=dict(wins=0, losses=0, pushes=0, lined_games=0),
                          ou=dict(overs=0, unders=0, pushes=0, lined_games=0), window_games=len(recent))
            for g, own, other in recent:
                line = lines.get(str(g["id"]), {})
                own_score, opp_score = number(g[own + "Points"]), number(g[other + "Points"])
                spread, total = number(line.get("spread")), number(line.get("overUnder"))
                if spread is not None:
                    margin = own_score - opp_score + (spread if own == "home" else -spread)
                    record["ats"]["lined_games"] += 1
                    record["ats"]["wins" if margin > 0 else "losses" if margin < 0 else "pushes"] += 1
                if total is not None and total > 0:
                    margin = own_score + opp_score - total
                    record["ou"]["lined_games"] += 1
                    record["ou"]["overs" if margin > 0 else "unders" if margin < 0 else "pushes"] += 1
            team.setdefault("form", {})["last5_market"] = record
        matchup["matchup_metrics"] = [m for m in matchup["matchup_metrics"] if m["label"] != "PPG"] + [pair]
    payload.setdefault("slate", {})["scoring_form"] = dict(
        results_collected_at=results["collected_at"],
        markets_collected_at=markets["collected_at"] if markets else None,
        method="Completed regular-season scoreboard points; last five completed games with available CFBD closing lines.")
    return payload


def main():
    root = Path(__file__).resolve().parents[1]
    path = root / "cfb-dashboard-preview/data/dashboard.json"
    read = lambda p: json.loads(p.read_text())
    market_path = root / "data/cfb/pipeline/markets.json"
    data = enrich(read(path), read(root / "data/cfb/pipeline/results.json"),
                  read(market_path) if market_path.exists() else None)
    if not data["games"]:
        raise ValueError("Refusing an empty CFB dashboard")
    path.write_text(json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")
    print("Published scoring and last-five market records for", len(data["games"]), "CFB matchups")


if __name__ == "__main__":
    main()
