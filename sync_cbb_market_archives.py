#!/usr/bin/env python3
"""Capture actual pre-tipoff CBB odds and publish verified 2026-27 team ATS/O-U records.

An ESPN quote first observed after scheduled tipoff is NEVER used as a result line.
This supplements existing historical market archives without rewriting older seasons.
"""
import json
import os
import re
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SEASON = 2027
LEDGER = ROOT / "data/cbb/pregame-markets/2027.json"
MARKETS = ROOT / "data/cbb/markets"
TEAMS = ROOT / "data/cbb/teams"
URL = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?groups=50&limit=1000&dates="

def timestamp(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))

def number(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None

def capture_event(e, now):
    if str(e.get("season", {}).get("year")) != str(SEASON):
        return None
    tip = timestamp(e["date"])
    if now >= tip or e.get("status", {}).get("type", {}).get("completed"):
        return None
    comps = e.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    sides = {v.get("homeAway"): v for v in comp.get("competitors", [])}
    if set(sides) != {"home", "away"}:
        return None
    odds = comp.get("odds") or []
    if not odds:
        return None
    q = odds[0]
    magnitude = number(q.get("spread"))
    home_fav = q.get("homeTeamOdds", {}).get("favorite")
    away_fav = q.get("awayTeamOdds", {}).get("favorite")
    home_spread = None
    if magnitude == 0:
        home_spread = 0.0
    elif magnitude is not None and home_fav is True and away_fav is not True:
        home_spread = -abs(magnitude)
    elif magnitude is not None and away_fav is True and home_fav is not True:
        home_spread = abs(magnitude)
    total = number(q.get("overUnder"))
    if home_spread is None and total is None:
        return None
    return {
        "id": str(e["id"]), "tipoff": e["date"], "observed_at": now.isoformat(),
        "home": str(sides["home"]["team"]["id"]), "away": str(sides["away"]["team"]["id"]),
        "home_spread": home_spread, "total": total,
        "provider": q.get("provider", {}).get("name"),
        "source": URL + tip.astimezone(ZoneInfo("America/New_York")).strftime("%Y%m%d"),
        "line_type": "ESPN pregame observed; not verified closing line",
    }


def canonical(name):
    s=unicodedata.normalize("NFKD",str(name)).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]","",s.replace("saint ","st ").replace("state ","state "))

def fetch_cbbd_lines(now):
    """Authenticated archived provider odds, backfill recent games without pretending live observation."""
    key=os.getenv("CBBD_API_KEY")
    if not key:
        print("CBBD_API_KEY unavailable; skipping CBBD odds fallback")
        return []
    end=(now+timedelta(days=8)).isoformat()
    start=(now-timedelta(days=14)).isoformat()
    params=urllib.parse.urlencode({"season":SEASON,"startDateRange":start,"endDateRange":end})
    url="https://api.collegebasketballdata.com/lines?"+params
    req=urllib.request.Request(url,headers={"Authorization":"Bearer "+key,"Accept":"application/json","User-Agent":"BetWiseCBBD/1.0"})
    with urllib.request.urlopen(req,timeout=60) as response:
        payload=json.load(response)
    if not isinstance(payload,list):raise ValueError("CBBD lines API did not return a list")
    return payload

def incorporate_cbbd(entries, rows):
    registry=json.loads((ROOT/"data/sports/team-registry.json").read_text())
    aliases={}
    for team in registry["teams"]:
        if team.get("sport")!="cbb":continue
        keys=[team.get("short_name"),team.get("name"),*team.get("aliases",[])]
        for key in keys:
            if key and canonical(key):
                aliases.setdefault(canonical(key),set()).add(str(team["espn_id"]))
    candidates={}
    for row in rows:
        home=aliases.get(canonical(row.get("homeTeam")),set())
        away=aliases.get(canonical(row.get("awayTeam")),set())
        if len(home)!=1 or len(away)!=1:continue
        h,a=next(iter(home)),next(iter(away))
        if h==a:continue
        for line in row.get("lines") or []:
            provider=line.get("provider")
            spread=number(line.get("spread"))
            total=number(line.get("overUnder"))
            if spread is None and total is None:continue
            candidates.setdefault((h,a),[]).append((row,line))
    matched=0
    # Match against ESPN's final-game archives by exact participants, scores and date.
    by_id={}
    for file in TEAMS.glob("*.json"):
        team=json.loads(file.read_text())
        for phase in team.get("seasons",{}).get(str(SEASON),{}).get("phases",{}).values():
            for g in phase.get("games",[]):
                if g.get("status")!="final":continue
                by_id.setdefault(str(g["id"]),[]).append((str(team["team_id"]),g))
    for gid, sides in by_id.items():
        if len(sides)!=2:continue
        (id1,g1),(id2,g2)=sides
        matching=[]
        for home,away in ((id1,id2),(id2,id1)):
            for row,line in candidates.get((home,away),[]):
                try:
                    game_day=timestamp(g1["date"]).date()
                    api_day=timestamp(row["startDate"]).date()
                    if abs((game_day-api_day).days)>1:continue
                    hs=number(row.get("homeScore"));ascore=number(row.get("awayScore"))
                    homegame=g1 if id1==home else g2
                    awaygame=g2 if id1==home else g1
                    if hs is None or ascore is None or hs!=number(homegame["points"]) or ascore!=number(awaygame["points"]):continue
                    matching.append((home,away,row,line))
                except (KeyError,ValueError,TypeError):continue
        if not matching:continue
        # Consistent provider selection; do not merge potentially contradictory lines.
        matching.sort(key=lambda x:(0 if str(x[3].get("provider","")).lower()=="consensus" else 1,
                                    str(x[3].get("provider",""))))
        home,away,row,line=matching[0]
        prior=entries.get(gid)
        if prior and prior.get("home")==home and prior.get("away")==away and prior.get("home_spread") is not None and prior.get("total") is not None:
            continue
        new={"id":gid,"tipoff":g1["date"],"observed_at":row.get("startDate",g1["date"]),
             "home":home,"away":away,"home_spread":number(line.get("spread")),
             "total":number(line.get("overUnder")),"provider":line.get("provider"),
             "source":"https://api.collegebasketballdata.com/lines?season=2027",
             "line_type":"CBBD archived provider line; closing not independently verified",
             "source_type":"archived_provider"}
        if prior and prior.get("home")==home and prior.get("away")==away:
            for field in ("home_spread","total"):
                if prior.get(field) is not None:new[field]=prior[field]
        entries[gid]=new
        matched+=1
    return matched

def update(now=None, fetch=None, *, capture=True):
    now = now or datetime.now(timezone.utc)
    def load(url):
        req = urllib.request.Request(url, headers={"User-Agent": "BetWiseCBBMarkets/1.0"})
        with urllib.request.urlopen(req, timeout=35) as response:
            return json.load(response)
    fetch = fetch or load
    old = json.loads(LEDGER.read_text()) if LEDGER.exists() else {"season": SEASON, "games": {}}
    if int(old["season"]) != SEASON:
        raise ValueError("Wrong market ledger season")
    entries = old.setdefault("games", {})
    day = now.astimezone(ZoneInfo("America/New_York")).date()
    observed = 0
    for offset in range(8 if capture else 0):
        board = fetch(URL + (day + timedelta(days=offset)).strftime("%Y%m%d"))
        for e in board.get("events", []):
            row = capture_event(e, now)
            if row:
                prev = entries.get(row["id"])
                if prev:
                    # Preserve a previously verified side when a later quote omits it.
                    for field in ("home_spread", "total"):
                        if row[field] is None:
                            row[field] = prev.get(field)
                entries[row["id"]] = row
                observed += 1
    archived_matched=incorporate_cbbd(entries,fetch_cbbd_lines(now)) if capture and os.getenv("CBBD_API_KEY") else 0
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    new_ledger = {"season": SEASON, "last_checked": now.isoformat(), "games": entries}
    if capture:
        LEDGER.write_text(json.dumps(new_ledger, separators=(",", ":")) + "\n")
    count = 0
    for path in sorted(TEAMS.glob("*.json")):
        team = json.loads(path.read_text())
        current = team.get("seasons", {}).get(str(SEASON), {})
        completed = current.get("phases", {}).get("regular", {}).get("games", [])
        completed += current.get("phases", {}).get("postseason", {}).get("games", [])
        previous_path = MARKETS / path.name
        archive = json.loads(previous_path.read_text()) if previous_path.exists() else {"seasons": {}, "games": {}}
        games = {}
        ats = [0, 0, 0]
        ou = [0, 0, 0]
        for game in completed:
            if game.get("status") != "final":
                continue
            odds = entries.get(str(game["id"]))
            if not odds or (odds.get("source_type")!="archived_provider" and timestamp(odds["observed_at"]) >= timestamp(odds["tipoff"])):
                continue
            pts, opp = number(game.get("points")), number(game.get("opponent_points"))
            if pts is None or opp is None:
                continue
            side = "home" if odds["home"] == str(team["team_id"]) else "away" if odds["away"] == str(team["team_id"]) else None
            if side is None:
                continue
            result = {"observed_at": odds["observed_at"], "source": odds["source"], "provider": odds.get("provider"), "line_type": odds["line_type"]}
            if odds.get("home_spread") is not None:
                spread = odds["home_spread"] if side == "home" else -odds["home_spread"]
                diff = pts - opp + spread
                outcome = "W" if diff > 0 else "L" if diff < 0 else "P"
                result.update(spread=spread, ats=outcome)
                ats[{"W": 0, "L": 1, "P": 2}[outcome]] += 1
            if odds.get("total") is not None:
                diff = pts + opp - odds["total"]
                outcome = "O" if diff > 0 else "U" if diff < 0 else "P"
                result.update(total=odds["total"], ou=outcome)
                ou[{"O": 0, "U": 1, "P": 2}[outcome]] += 1
            if "ats" in result or "ou" in result:
                games[str(game["id"])] = result
        if games or str(SEASON) in archive.get("games", {}):
            archive.setdefault("games", {})[str(SEASON)] = games
            archive.setdefault("seasons", {})[str(SEASON)] = {
                "ats": ats, "ou": ou, "source": "ESPN pregame observed lines",
                "coverage": "Only lines captured before scheduled tipoff; unlined games excluded",
                "expected_games": len([g for g in completed if g.get("status") == "final"]),
            }
            previous_path.parent.mkdir(parents=True, exist_ok=True)
            previous_path.write_text(json.dumps(archive, separators=(",", ":")) + "\n")
            count += 1
    print(json.dumps({"observed_upcoming_games": observed, "pregame_ledger_games": len(entries), "updated_team_market_files": count, "cbbd_archived_games_matched": archived_matched}))
    return new_ledger

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--grade-only", action="store_true")
    update(capture=not parser.parse_args().grade_only)
