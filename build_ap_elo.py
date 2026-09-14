#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "raw"
YEARS = range(2015, 2027)


def norm(value: str) -> str:
    aliases = {
        "Miami (FL)": "Miami",
        "Miami (Fla.)": "Miami",
        "Ole Miss": "Mississippi",
        "UTSA": "Texas-San Antonio",
        "UConn": "Connecticut",
    }
    value = " ".join(value.split()).strip()
    return aliases.get(value, value)


def ap_by_week(payload: list[dict]) -> dict[int, dict[str, dict]]:
    out: dict[int, dict[str, dict]] = {}
    for snapshot in payload:
        week = int(snapshot["week"])
        ap = next((p for p in snapshot.get("polls", [])
                   if p.get("poll", "").casefold() in {"ap top 25", "ap"}), None)
        if not ap:
            continue
        ranks = ap.get("ranks", [])
        rank_values = [int(r["rank"]) for r in ranks]
        schools = [norm(r["school"]) for r in ranks]
        # AP ties are official. A tie at No. 25 can produce 26 listed teams and
        # an earlier tie can skip the following ordinal rank.
        valid_size = len(ranks) in {25, 26}
        valid_range = all(1 <= rank <= 25 for rank in rank_values)
        ordered = sorted(rank_values)
        valid_competition_ranks = bool(ordered) and ordered[0] == 1 and all(
            rank == ordered[position - 2] or rank == position
            for position, rank in enumerate(ordered, 1) if position > 1
        )
        valid_teams = len(schools) == len(set(schools))
        if not (valid_size and valid_range and valid_competition_ranks and valid_teams):
            raise ValueError(f"Invalid AP board: season={snapshot['season']} week={week}")
        out[week] = {norm(r["school"]): r for r in ranks}
    return out


def rank_elos(ratings: dict[str, int], field_size: int) -> dict[str, dict]:
    rows = [{"team": team, "elo": elo} for team, elo in ratings.items() if elo is not None]
    rows.sort(key=lambda r: (-int(r["elo"]), norm(r["team"])))
    # Competition ranking is deterministic for tied Elo values.
    last_elo = None
    last_rank = 0
    out = {}
    for position, row in enumerate(rows, 1):
        rating = int(row["elo"])
        if rating != last_elo:
            last_rank = position
            last_elo = rating
        out[norm(row["team"])] = {
            "rating": rating,
            "rank": last_rank,
            "field": field_size,
        }
    available = [int(v) for v in ratings.values() if v is not None]
    for item in out.values():
        rating = item["rating"]
        below = sum(v < rating for v in available)
        tied = sum(v == rating for v in available)
        percentile = 100.0 if len(available) <= 1 else (
            100.0 * (below + (tied - 1) / 2) / (len(available) - 1)
        )
        score = max(1, min(100, int(percentile + 0.5)))
        item["strength_score"] = score
        item["strength_tier"] = (
            "Elite" if score >= 90 else "Strong" if score >= 75 else
            "Above Average" if score >= 50 else "Below Average" if score >= 25 else "Weak"
        )
        item["top_percent"] = 101 - score
    return out


def weekly_elo_boards(roster_payload: list[dict], games: list[dict], weeks: list[int]) -> dict[int, dict[str, dict]]:
    roster = {norm(t["school"]) for t in roster_payload}
    team_games = {team: [] for team in roster}
    for game in sorted(games, key=lambda g: (int(g.get("week") or 0), g.get("startDate") or "")):
        for side in ("home", "away"):
            team = norm(game.get(f"{side}Team") or "")
            if team in roster:
                team_games[team].append({
                    "week": int(game.get("week") or 0),
                    "date": game.get("startDate") or "",
                    "pregame": game.get(f"{side}PregameElo"),
                    "postgame": game.get(f"{side}PostgameElo"),
                })

    boards = {}
    for target_week in sorted(weeks):
        ratings = {}
        for team in roster:
            schedule = team_games[team]
            same_or_next = next((g for g in schedule if g["week"] >= target_week and g["pregame"] is not None), None)
            if same_or_next:
                ratings[team] = int(same_or_next["pregame"])
                continue
            prior = [g for g in schedule if g["week"] < target_week and g["postgame"] is not None]
            if prior:
                ratings[team] = int(prior[-1]["postgame"])
        boards[target_week] = rank_elos(ratings, len(roster))
    return boards


def compile_rows() -> tuple[list[dict], list[dict]]:
    rows = []
    game_rows = []
    for season in YEARS:
        rankings_path = RAW / f"rankings_{season}.json"
        if not rankings_path.exists():
            continue
        ap_weeks = ap_by_week(json.loads(rankings_path.read_text()))
        roster_path = RAW / f"teams_fbs_{season}.json"
        games_path = RAW / f"games_{season}.json"
        if not roster_path.exists() or not games_path.exists():
            continue
        roster_payload = json.loads(roster_path.read_text())
        games_payload = json.loads(games_path.read_text())
        elo_weeks = weekly_elo_boards(
            roster_payload,
            games_payload,
            list(ap_weeks),
        )
        for effective_week, ap in sorted(ap_weeks.items()):
            elo_snapshot_week = effective_week
            elo = elo_weeks[effective_week]
            teams = sorted({norm(t["school"]) for t in roster_payload})
            for team in teams:
                poll = ap.get(team)
                strength = elo.get(team)
                rows.append({
                    "season": season,
                    "effective_week": effective_week,
                    "team": team,
                    "is_ap_ranked": bool(poll),
                    "ap_rank": int(poll["rank"]) if poll else None,
                    "ap_points": poll.get("points") if poll else None,
                    "ap_first_place_votes": poll.get("firstPlaceVotes") if poll else None,
                    "elo_rating": strength["rating"] if strength else None,
                    "elo_rank": strength["rank"] if strength else None,
                    "strength_score": strength["strength_score"] if strength else None,
                    "strength_tier": strength["strength_tier"] if strength else None,
                    "top_percent": strength["top_percent"] if strength else None,
                    "fbs_field_size": len(teams),
                    "ap_source_week": effective_week,
                    "elo_snapshot_week": elo_snapshot_week,
                    "timing_status": "PREGAME_SAFE",
                })

            base_ratings = {team: item["rating"] for team, item in elo.items()}
            roster = set(teams)
            for game in games_payload:
                if int(game.get("week") or 0) != effective_week:
                    continue
                for side in ("home", "away"):
                    team = norm(game.get(f"{side}Team") or "")
                    if team not in roster:
                        continue
                    direct_rating = game.get(f"{side}PregameElo")
                    rating = direct_rating if direct_rating is not None else base_ratings.get(team)
                    poll = ap.get(team)
                    ranked = None
                    if rating is not None:
                        at_kickoff = dict(base_ratings)
                        at_kickoff[team] = int(rating)
                        ranked = rank_elos(at_kickoff, len(teams)).get(team)
                    game_rows.append({
                        "game_id": game["id"],
                        "season": season,
                        "week": effective_week,
                        "start_date": game.get("startDate"),
                        "team": team,
                        "side": side,
                        "opponent": norm(game.get("awayTeam") if side == "home" else game.get("homeTeam")),
                        "is_ap_ranked": bool(poll),
                        "ap_rank": int(poll["rank"]) if poll else None,
                        "pregame_elo": int(rating) if rating is not None else None,
                        "pregame_elo_rank": ranked["rank"] if ranked else None,
                        "strength_score": ranked["strength_score"] if ranked else None,
                        "strength_tier": ranked["strength_tier"] if ranked else None,
                        "top_percent": ranked["top_percent"] if ranked else None,
                        "elo_source": "GAME_PREGAME" if direct_rating is not None else ("WEEKLY_CARRY" if rating is not None else "UNAVAILABLE"),
                        "fbs_field_size": len(teams),
                        "timing_status": "PREGAME_SAFE" if rating is not None else "ELO_UNAVAILABLE",
                    })
    return rows, game_rows


def write_outputs(rows: list[dict], game_rows: list[dict]) -> None:
    fields = [
        "season", "effective_week", "team", "is_ap_ranked", "ap_rank",
        "ap_points", "ap_first_place_votes", "elo_rating", "elo_rank",
        "strength_score", "strength_tier", "top_percent", "fbs_field_size", "ap_source_week", "elo_snapshot_week", "timing_status",
    ]
    with (ROOT / "match_lab_ap_elo_master.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    lookup = {"schema_version": "3.0", "display_metric": "Team Strength", "data": {}}
    for r in rows:
        leaf = lookup["data"].setdefault(str(r["season"]), {}).setdefault(str(r["effective_week"]), {})
        leaf[r["team"]] = {
            "ap_rank": r["ap_rank"],
            "elo_rating": r["elo_rating"],
            "elo_rank": r["elo_rank"],
            "strength_score": r["strength_score"],
            "strength_tier": r["strength_tier"],
            "top_percent": r["top_percent"],
            "fbs_field_size": r["fbs_field_size"],
        }
    (ROOT / "match_lab_ap_elo_lookup.json").write_text(
        json.dumps(lookup, separators=(",", ":")), encoding="utf-8"
    )

    game_fields = [
        "game_id", "season", "week", "start_date", "team", "side", "opponent",
        "is_ap_ranked", "ap_rank", "pregame_elo", "pregame_elo_rank",
        "strength_score", "strength_tier", "top_percent", "elo_source",
        "fbs_field_size", "timing_status",
    ]
    with (ROOT / "match_lab_game_ap_elo.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=game_fields)
        writer.writeheader()
        writer.writerows(game_rows)
    game_lookup = {"schema_version": "3.0", "display_metric": "Team Strength", "data": {}}
    for r in game_rows:
        game_lookup["data"].setdefault(str(r["game_id"]), {})[r["team"]] = {
            "ap_rank": r["ap_rank"],
            "pregame_elo": r["pregame_elo"],
            "pregame_elo_rank": r["pregame_elo_rank"],
            "strength_score": r["strength_score"],
            "strength_tier": r["strength_tier"],
            "top_percent": r["top_percent"],
            "fbs_field_size": r["fbs_field_size"],
        }
    (ROOT / "match_lab_game_ap_elo_lookup.json").write_text(
        json.dumps(game_lookup, separators=(",", ":")), encoding="utf-8"
    )

    coverage = []
    grouped = {}
    for r in rows:
        grouped.setdefault((r["season"], r["effective_week"]), []).append(r)
    for (season, week), rr in sorted(grouped.items()):
        ranked = [r for r in rr if r["is_ap_ranked"]]
        errors = []
        if len(ranked) not in {25, 26}:
            errors.append(f"AP count={len(ranked)}")
        ordered_ap = sorted(r["ap_rank"] for r in ranked)
        if not ordered_ap or ordered_ap[0] != 1 or not all(
            rank == ordered_ap[position - 2] or rank == position
            for position, rank in enumerate(ordered_ap, 1) if position > 1
        ):
            errors.append("AP competition ranks invalid")
        if any(r["elo_snapshot_week"] != week for r in rr):
            errors.append("Elo snapshot week mismatch")
        elo_missing = [r["team"] for r in rr if r["elo_rating"] is None]
        coverage.append({
            "season": season,
            "effective_week": week,
            "team_count": len(rr),
            "ap_ranked_count": len(ranked),
            "elo_count": sum(r["elo_rating"] is not None for r in rr),
            "strength_score_count": sum(r["strength_score"] is not None for r in rr),
            "strength_score_status": "PASS" if all((r["elo_rating"] is None) == (r["strength_score"] is None) for r in rr) else "FAIL",
            "status": "FAIL" if errors else ("PASS_WITH_INACTIVE_UNAVAILABLE" if elo_missing else "PASS"),
            "issues": "; ".join(errors) if errors else ("Elo unavailable: " + ", ".join(elo_missing) if elo_missing else ""),
        })
    with (ROOT / "match_lab_ap_elo_coverage.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(coverage[0]) if coverage else ["season"])
        writer.writeheader()
        writer.writerows(coverage)


if __name__ == "__main__":
    compiled, game_compiled = compile_rows()
    if not compiled:
        raise SystemExit("No raw API responses found. Nothing was published.")
    write_outputs(compiled, game_compiled)
    print(f"Built {len(compiled):,} pregame team-week rows and {len(game_compiled):,} game-team rows")
