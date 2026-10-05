"""Raw sack rates and turnover totals from paired CFBD team box scores."""
def numeric(value):
    try:
        return float(value) if value not in (None, "") else None
    except (ValueError, TypeError):
        return None

def attempts(value):
    if value is None:
        return None
    for separator in ("-", "/"):
        parts = str(value).split(separator)
        if len(parts) == 2:
            return numeric(parts[1])
    return None

def box_stats(team):
    return {"".join(c.lower() for c in str(s.get("category", "")) if c.isalnum()): s.get("stat") for s in team.get("stats", [])}

def accumulate_boxes(games, totals, canon=lambda name: name):
    for game in games:
        teams = game.get("teams", [])
        if len(teams) != 2:
            continue
        for i, team in enumerate(teams):
            name = canon(team.get("team"))
            if not name:
                continue
            own, opponent = box_stats(team), box_stats(teams[1-i])
            row = totals.setdefault(name, {"games": 0, "sack_games": 0, "turnover_games": 0, "sacks": 0, "sacks_allowed": 0, "dropbacks": 0, "opponent_dropbacks": 0, "turnovers": 0, "turnovers_forced": 0})
            row["games"] += 1
            sacks, allowed = numeric(own.get("sacks")), numeric(opponent.get("sacks"))
            passes = attempts(own.get("completionattempts") or own.get("completionsattempts"))
            opponent_passes = attempts(opponent.get("completionattempts") or opponent.get("completionsattempts"))
            if all(v is not None for v in (sacks, allowed, passes, opponent_passes)):
                row["sack_games"] += 1
                row["sacks"] += sacks
                row["sacks_allowed"] += allowed
                row["dropbacks"] += passes + allowed
                row["opponent_dropbacks"] += opponent_passes + sacks
            lost, forced = numeric(own.get("turnovers")), numeric(opponent.get("turnovers"))
            if lost is not None and forced is not None:
                row["turnover_games"] += 1
                row["turnovers"] += lost
                row["turnovers_forced"] += forced

def season_metrics(row):
    sacks_complete = row["games"] > 0 and row["sack_games"] == row["games"]
    turnovers_complete = row["games"] > 0 and row["turnover_games"] == row["games"]
    return {
        "sack_rate_allowed": row["sacks_allowed"] / row["dropbacks"] if sacks_complete and row["dropbacks"] else None,
        "sack_rate": row["sacks"] / row["opponent_dropbacks"] if sacks_complete and row["opponent_dropbacks"] else None,
        "turnovers": int(row["turnovers"]) if turnovers_complete else None,
        "turnovers_forced": int(row["turnovers_forced"]) if turnovers_complete else None,
    }
