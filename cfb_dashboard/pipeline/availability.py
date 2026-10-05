"""Current reported availability. Missing reports are unknown, never confirmed healthy."""
import json
import re
import urllib.request
from datetime import datetime, timezone

OUT = {"out", "doubtful", "injured reserve", "ir", "suspended", "pup", "nfi", "res", "sus"}

def name_key(name):
    words = re.sub(r"[^a-z0-9 ]", "", str(name).lower()).split()
    return " ".join(w for w in words if w not in {"jr", "sr", "ii", "iii", "iv"})

def current_reports(payload, now, league):
    reports = {}
    for group in payload.get("injuries", []):
        for report in group.get("injuries", []):
            try:
                stamp = datetime.fromisoformat(report["date"].replace("Z", "+00:00"))
                if stamp.tzinfo is None: stamp = stamp.replace(tzinfo=timezone.utc)
            except (KeyError, ValueError, TypeError): continue
            status = str(report.get("status") or "").lower()
            age = (now - stamp).total_seconds() / 86400
            season_long = status in {"injured reserve", "ir", "suspended", "pup", "nfi"}
            if stamp.year != now.year or age < -1 or (age > 10 and not season_long): continue
            athlete = report.get("athlete") or {}
            team = str(group.get("id") or "") if league == "college-football" else (athlete.get("team") or {}).get("abbreviation", "")
            team = {"WSH":"WAS", "LAR":"LA"}.get(team, team)
            athlete_id = str(athlete.get("id") or "")
            if not athlete_id:
                for link in athlete.get("links", []):
                    match = re.search(r"/id/(\d+)", link.get("href", ""))
                    if match: athlete_id = match.group(1); break
            value = {"status": report.get("status"), "unavailable": status in OUT,
                     "availability_updated": stamp.isoformat(), "availability_note": "Reported " + str(report.get("status") or "Unknown")}
            for key in (["id:" + athlete_id] if athlete_id else []) + ["name:" + name_key(athlete.get("displayName"))]:
                prior = reports.get((team, key))
                if not prior or value["availability_updated"] > prior["availability_updated"]: reports[(team, key)] = value
    return reports

def fetch_reports(league, now):
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/football/{league}/injuries"
        request = urllib.request.Request(url, headers={"User-Agent":"BetWise/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response: payload = json.load(response)
        return current_reports(payload, now, league)
    except Exception as exc:
        print(f"Availability feed unavailable ({type(exc).__name__}); retaining roster/projection fallback")
        return {}

def lookup(reports, team, player_id, name):
    return reports.get((str(team), "id:" + str(player_id))) or reports.get((str(team), "name:" + name_key(name))) or {}
