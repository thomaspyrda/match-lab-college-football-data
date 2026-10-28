"""Season-to-date ranking inputs from the completed ESPN regular-season cache."""
from collections import defaultdict
import math
from datetime import datetime
from zoneinfo import ZoneInfo

BOX_KEYS = ("points", "fgm", "fga", "tpm", "tpa", "ftm", "fta", "oreb",
            "dreb", "reb", "ast", "tov", "stl", "blk")


def ratio(a, b, scale=100):
    return a / b * scale if b else None


def game_minutes(game):
    periods = game.get("periods")
    if isinstance(periods, int) and periods >= 4:
        return 48 + 5 * (periods - 4)
    # Older cache entries contain player minutes but no final period number.
    totals = [sum(p.get("minutes") or 0 for p in game.get("players", {}).get(tid, []))
              for tid in game["teams"]]
    if len(totals) == 2 and min(totals) >= 230:
        elapsed = sum(totals) / 10
        return 48 + 5 * max(0, round((elapsed - 48) / 5))
    return None


def build_current_rows(cache, registry, team_info, year, metric_keys):
    lookup = {str(t["espn_id"]): t["slug"] for t in registry["teams"]
              if t.get("sport") == "nba"}
    if set(lookup.values()) != set(team_info):
        raise ValueError("Current-season registry must contain exactly the 30 NBA teams")
    grouped = {slug: [] for slug in team_info}
    selected = {}
    for game in cache.get("games", []):
        if game.get("season") != year or game.get("phase") != 2:
            continue
        gid = str(game["id"])
        if gid in selected:
            if selected[gid] != game:
                raise ValueError("Conflicting duplicate NBA game " + gid)
            continue
        teams = game.get("teams", {})
        if len(teams) != 2 or any(tid not in lookup for tid in teams):
            raise ValueError("Unknown NBA game participants: " + gid)
        for box in teams.values():
            if any(not isinstance(box.get(k), (int, float)) or not math.isfinite(box[k]) or box[k] < 0 for k in BOX_KEYS):
                raise ValueError("Incomplete NBA box score: " + gid)
            if abs(2 * box["fgm"] + box["tpm"] + box["ftm"] - box["points"]) > .01:
                raise ValueError("NBA box score does not reconcile to points: " + gid)
            if not (box["tpm"] <= box["fgm"] <= box["fga"] and
                    box["tpm"] <= box["tpa"] <= box["fga"] and box["ftm"] <= box["fta"]):
                raise ValueError("Invalid NBA shooting totals: " + gid)
        if game.get("home") not in teams:
            raise ValueError("Missing NBA home team: " + gid)
        ids = list(teams)
        if teams[ids[0]]["points"] == teams[ids[1]]["points"]:
            raise ValueError("Completed NBA game cannot be tied: " + gid)
        selected[gid] = game
        for tid in teams:
            grouped[lookup[tid]].append((game, tid))
    rows = []
    for slug, (name, abbr, conference, division) in team_info.items():
        games = grouped[slug]
        n = len(games)
        metrics = dict.fromkeys(metric_keys)
        own, opp = defaultdict(float), defaultdict(float)
        possessions = elapsed = 0
        minutes_known = True
        wins = 0
        splits = {venue: [] for venue in ("Home", "Away")}
        for game, tid in games:
            a = game["teams"][tid]
            b = game["teams"][next(i for i in game["teams"] if i != tid)]
            for k in BOX_KEYS:
                own[k] += a[k]
                opp[k] += b[k]
            possessions += (a["fga"] - a["oreb"] + a["tov"] + .44 * a["fta"] +
                            b["fga"] - b["oreb"] + b["tov"] + .44 * b["fta"]) / 2
            duration = game_minutes(game)
            minutes_known &= duration is not None
            elapsed += duration or 0
            wins += a["points"] > b["points"]
            if not game.get("neutral"):
                splits["Home" if game["home"] == tid else "Away"].append((a["points"], b["points"]))
        if n:
            if possessions <= 0:
                raise ValueError("Invalid estimated NBA possessions: " + slug)
            for key, box_key in {"ppg": "points", "assists_per_game": "ast",
                                 "turnovers_per_game": "tov", "rebounds_per_game": "reb",
                                 "steals_per_game": "stl", "blocks_per_game": "blk"}.items():
                metrics[key] = own[box_key] / n
            for key, box_key in {"ppg_allowed": "points", "opponent_assists_per_game": "ast",
                                 "opponent_turnovers_per_game": "tov", "rebounds_allowed_per_game": "reb",
                                 "opponent_steals_per_game": "stl", "opponent_blocks_per_game": "blk"}.items():
                metrics[key] = opp[box_key] / n
            for prefix, box in (("", own), ("opp_", opp)):
                metrics[prefix + "fg_pct"] = ratio(box["fgm"], box["fga"])
                metrics[prefix + "three_pct"] = ratio(box["tpm"], box["tpa"])
                metrics[prefix + "efg_pct"] = ratio(box["fgm"] + .5 * box["tpm"], box["fga"])
                metrics[prefix + "tov_pct"] = ratio(box["tov"], box["fga"] + .44 * box["fta"] + box["tov"])
            metrics.update({
                "ortg": ratio(own["points"], possessions),
                "drtg": ratio(opp["points"], possessions),
                "net_rating": ratio(own["points"] - opp["points"], possessions),
                "pace": possessions * 48 / elapsed if minutes_known else None,
                "ts_pct": ratio(own["points"], 2 * (own["fga"] + .44 * own["fta"])),
                "ft_pct": ratio(own["ftm"], own["fta"]),
                "three_attempt_rate": ratio(own["tpa"], own["fga"]),
                "ft_rate": ratio(own["fta"], own["fga"]),
                "ft_made_rate": ratio(own["ftm"], own["fga"]),
                "opp_ft_made_rate": ratio(opp["ftm"], opp["fga"]),
                "orb_pct": ratio(own["oreb"], own["oreb"] + opp["dreb"]),
                "drb_pct": ratio(own["dreb"], own["dreb"] + opp["oreb"]),
                "turnover_margin": (opp["tov"] - own["tov"]) / n,
            })
            metrics["offensive_rebound_rate"] = metrics["orb_pct"]
            metrics["defensive_rebound_rate"] = metrics["drb_pct"]
            paint = [g["teams"][next(i for i in g["teams"] if i != tid)].get("paint_points") for g, tid in games]
            metrics["opp_points_in_paint"] = sum(paint) / n if all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in paint) else None
            for venue, entries in splits.items():
                suffix = venue.lower()
                metrics["ppg_" + suffix] = sum(x[0] for x in entries) / len(entries) if entries else None
                metrics["ppg_allowed_" + suffix] = sum(x[1] for x in entries) / len(entries) if entries else None
        metrics = {k: round(v, 4) if v is not None else None for k, v in metrics.items()}
        rows.append({"slug": slug, "team": name, "abbreviation": abbr,
                     "conference": conference, "division": division,
                     "logo": f"https://a.espncdn.com/i/teamlogos/nba/500/{abbr.lower()}.png",
                     "record": f"{wins}–{n - wins}", "games_played": n,
                     "metrics": metrics, "ratings": {}, "ranks": {}})
    dates = [datetime.fromisoformat(g["date"].replace("Z", "+00:00")).astimezone(
             ZoneInfo("America/New_York")).date().isoformat() for g in selected.values()]
    return rows, {"completed_games": len(selected), "ranked_teams": sum(bool(v) for v in grouped.values()),
                  "through_date": max(dates) if dates else None,
                  "data_updated_at": max((g["observed_complete_at"] for g in selected.values()), default=None)}
