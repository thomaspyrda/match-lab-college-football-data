#!/usr/bin/env python3
"""Shared, source-neutral validation for daily NBA, MLB, and CBB backfills.

No external data is fetched here: sport adapters must supply observations from a
permitted source. Never infer absent betting odds or overwrite observed snapshots.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping

SUPPORTED_SPORTS = ("nba", "mlb", "cbb")

@dataclass(frozen=True)
class GameObservation:
    sport: str
    game_id: str
    observed_at: str
    game_date: str
    home_id: str
    away_id: str
    status: str
    home_score: int | None = None
    away_score: int | None = None

    def validate(self) -> None:
        if self.sport not in SUPPORTED_SPORTS:
            raise ValueError("unsupported sport")
        if not self.game_id or not self.home_id or not self.away_id or self.home_id == self.away_id:
            raise ValueError("invalid game/team identifiers")
        datetime.fromisoformat(self.game_date)
        instant = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        if instant.tzinfo is None:
            raise ValueError("observation timestamp must specify timezone")
        if self.status == "final":
            if self.home_score is None or self.away_score is None or min(self.home_score, self.away_score) < 0:
                raise ValueError("final game requires nonnegative scores")
        elif self.home_score is not None or self.away_score is not None:
            raise ValueError("non-final games cannot become recorded results")

def market_result(sport: str, home_score: int, away_score: int,
                  *, home_spread: float | None = None,
                  total: float | None = None) -> Mapping[str, str | None]:
    """Return home-side ATS/run-line and total outcomes, without guessing lines."""
    if sport not in SUPPORTED_SPORTS:
        raise ValueError("unsupported sport")
    if min(home_score, away_score) < 0:
        raise ValueError("invalid score")
    def result(delta: float) -> str:
        return "W" if delta > 0 else "L" if delta < 0 else "P"
    return {
        "home_ats_or_runline": result(home_score - away_score + home_spread) if home_spread is not None else None,
        "ou": ("Over" if home_score + away_score > total else "Under" if home_score + away_score < total else "Push") if total is not None else None,
    }

def accept_pregame_market(game_time: str, observed_at: str, market: Mapping) -> bool:
    """Allow only sourced odds observed before scheduled tipoff/first pitch."""
    tip = datetime.fromisoformat(game_time.replace("Z", "+00:00"))
    observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    if tip.tzinfo is None or observed.tzinfo is None:
        raise ValueError("timezone-aware timestamps required")
    return (observed < tip and bool(market.get("source")) and
            (market.get("home_spread") is not None or market.get("total") is not None))
