"""Require current-morning source collection after the morning grace window."""
from datetime import datetime
from zoneinfo import ZoneInfo

def require_morning_results(collected_at, now, sport):
    local = now.astimezone(ZoneInfo("America/New_York"))
    if local.hour >= 6:
        boundary = local.replace(hour=4, minute=0, second=0, microsecond=0)
        if datetime.fromisoformat(collected_at.replace("Z", "+00:00")) < boundary:
            raise ValueError(sport + " morning results collection is missing; prior-evening data is not a completed daily refresh")
