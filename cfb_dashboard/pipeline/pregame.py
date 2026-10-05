"""Pregame-safe helpers for the CFB Dashboard."""
from __future__ import annotations


def eligible_completed_games(games: list[dict], season: int, week: int) -> list[dict]:
    """Return only games completed before the requested week."""
    return [
        g for g in games
        if int(g.get("season", -1)) == int(season)
        and bool(g.get("completed"))
        and int(g.get("week", 999)) < int(week)
    ]


def team_prior_games(games: list[dict], team: str, season: int, week: int) -> list[dict]:
    """Completed games involving team before week; never future games."""
    prior = eligible_completed_games(games, season, week)
    return [
        g for g in prior
        if g.get("homeTeam") == team or g.get("awayTeam") == team
    ]


def record_before_week(games: list[dict], team: str, season: int, week: int) -> dict:
    wins = losses = 0
    for g in team_prior_games(games, team, season, week):
        home = g.get("homeTeam") == team
        pf = g.get("homePoints") if home else g.get("awayPoints")
        pa = g.get("awayPoints") if home else g.get("homePoints")
        if pf is None or pa is None:
            continue
        if pf > pa:
            wins += 1
        elif pf < pa:
            losses += 1
    return {"wins": wins, "losses": losses, "display": f"{wins}-{losses}"}
