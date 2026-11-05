"""Observed NBA quotes from scoreboard odds with game-summary fallback."""
import re
from nba_closing_markets import number


def _line(branch):
    if not isinstance(branch, dict):
        return None
    for kind in ("current", "close"):
        value = number((branch.get(kind) or {}).get("line"))
        if value is not None:
            return value
    return None


def parse_quote(quote, competition, observed_at):
    sides = {c.get("homeAway"): c.get("team", {}) for c in competition.get("competitors", [])}
    point = quote.get("pointSpread") or {}
    home = _line(point.get("home"))
    away = _line(point.get("away"))
    if home is not None and away is not None and abs(home + away) > .001:
        home = away = None
    if home is None and away is not None:
        home = -away
    details = quote.get("details")
    details = str(details).strip() if details is not None else None
    if details and not (re.search(r"[+-]\d+(?:\.\d+)?$", details) or details.upper() in {"PK", "PICK", "EVEN"}):
        details = None
    if home is None and details is None:
        spread = number(quote.get("spread"))
        if spread is not None:
            if (quote.get("homeTeamOdds") or {}).get("favorite") is True:
                home = -abs(spread)
            elif (quote.get("awayTeamOdds") or {}).get("favorite") is True:
                home = abs(spread)
            elif spread == 0:
                home = 0
    if home is not None:
        if home == 0:
            details = "PK"
        else:
            team = sides.get("home" if home < 0 else "away", {})
            name = team.get("abbreviation") or team.get("shortDisplayName") or team.get("displayName")
            details = str(name) + " -" + format(abs(home), "g") if name else None
    total = number(quote.get("overUnder"))
    branch = quote.get("total") or {}
    if total is None and isinstance(branch, dict):
        for kind in ("current", "close"):
            over = number(((branch.get("over") or {}).get(kind) or {}).get("line"), "o")
            under = number(((branch.get("under") or {}).get(kind) or {}).get("line"), "u")
            if over is not None and under is not None and abs(over - under) > .001:
                continue
            total = over if over is not None else under
            if total is not None:
                break
    if total is not None and total <= 0:
        total = None
    provider = quote.get("provider") or {}
    return {"spread": details, "total": total,
            "provider": provider.get("name") if isinstance(provider, dict) else str(provider),
            "observed_at": observed_at if details is not None or total is not None else None}


def current_market(event, observed_at, summary_loader=None):
    comp = (event.get("competitions") or [{}])[0]
    def best(quotes):
        parsed = [parse_quote(q, comp, observed_at) for q in quotes if isinstance(q, dict)]
        return max(parsed, key=lambda q: (q["spread"] is not None) + (q["total"] is not None), default=None)
    market = best(comp.get("odds") or [])
    if (not market or market["spread"] is None or market["total"] is None) and summary_loader:
        try:
            summary = summary_loader(str(event["id"]))
            candidate = best(summary.get("pickcenter") or [])
            if candidate and (not market or sum(candidate[k] is not None for k in ("spread", "total")) >
                              sum(market[k] is not None for k in ("spread", "total"))):
                market = candidate
        except Exception as exc:
            print("NBA quote summary unavailable for", event.get("id"), str(exc), flush=True)
    return market if market and market["observed_at"] else {
        "spread": None, "total": None, "provider": None, "observed_at": None}
