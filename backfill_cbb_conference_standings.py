"""Publish conference finishes from ESPN's season-specific conference records.

Historical seasons require --years explicitly. The default refreshes only the
active season, keeping completed seasons frozen. Championship labels require a
separately sourced title record; tournament seeds do not establish shared titles.
"""
import argparse
import json
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
SOURCE = "https://site.web.api.espn.com/apis/v2/sports/basketball/mens-college-basketball/standings?season={year}"
CONFERENCES = {
    "1": "America East", "62": "AAC", "3": "Atlantic 10", "2": "ACC",
    "46": "ASUN", "8": "Big 12", "4": "Big East", "5": "Big Sky",
    "6": "Big South", "7": "Big Ten", "9": "Big West", "10": "CAA",
    "11": "Conference USA", "45": "Horizon League", "12": "Ivy League",
    "13": "MAAC", "14": "MAC", "16": "MEAC", "18": "Missouri Valley",
    "44": "Mountain West", "19": "NEC", "20": "OVC", "21": "Pac-12",
    "22": "Patriot League", "23": "SEC", "24": "Southern Conference",
    "25": "Southland", "26": "SWAC", "49": "Summit League",
    "27": "Sun Belt", "30": "WAC", "29": "WCC",
}
EXCLUSIONS = {
    (2021, "28"): ("Conference games not counted in standings during Division I transition", "https://ucsdtritons.com/sports/mens-basketball/schedule/2020-21"),
    (2022, "28"): ("Conference games not counted in standings during Division I transition", "https://ucsdtritons.com/sports/mens-basketball/schedule/2021-22"),
}


def active_year(now=None):
    now = now or datetime.now(ZoneInfo("America/New_York"))
    return now.year + (now.month >= 7)


def ordinal(n):
    return str(n) + ("th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


def entries(group):
    rows = list(group.get("standings", {}).get("entries", []))
    for child in group.get("children", []):
        rows.extend(entries(child))
    return rows


def record(entry):
    # Stats repeat their names for home, away, overall and conference splits.
    # Only the explicit vsconf types are the regular-season conference record.
    stats = {s["type"]: s for s in entry.get("stats", [])}
    result = []
    for name in ("vsconf_wins", "vsconf_losses"):
        value = stats.get(name, {}).get("value")
        if value is None or value < 0 or int(value) != value:
            raise ValueError(f"Missing/invalid conference record for {entry['team']['id']}")
        result.append(int(value))
    return tuple(result)


def make_season(data, year, identities, championships, final=True):
    if int(data.get("season", {}).get("year", 0)) != year:
        raise ValueError("Standings response is for a different season")
    result, unmatched, seen = {}, [], set()
    for group in data.get("children", []):
        cid = str(group["id"])
        title_info = championships.get(str(year), {}).get(cid, {})
        if title_info.get("no_season"):
            for tid in title_info["team_ids"]:
                if tid in identities:
                    result[identities[tid]] = {"regular_season_result": "Season canceled (COVID-19) — No conference standings", "regular_season_standings": {"conference": CONFERENCES[cid], "conference_id": cid, "final": True, "rank": None, "status": "season_canceled", "source": title_info["source"]}}
            continue
        rows = entries(group)
        if not rows:
            continue
        label = CONFERENCES.get(cid, group.get("shortName") or group["name"])
        if cid == "62" and year >= 2026:
            label = "American Conference"
        if cid == "30" and year >= 2027:
            label = group.get("shortName") or group["name"]
        if cid == "13" and year >= 2027:
            label = group.get("shortName") or group["name"]
        records = {str(e["team"]["id"]): record(e) for e in rows if (year, str(e["team"]["id"])) not in EXCLUSIONS}
        ratios = {tid: Fraction(w, w + l) for tid, (w, l) in records.items() if w + l}
        basis = title_info.get("ranking_basis", "conference_win_percentage")
        if basis == "conference_wins":
            ratios = {tid: Fraction(w) for tid, (w, l) in records.items() if w + l}
        winners = {str(x) for x in title_info.get("champions", [])}
        for team in rows:
            tid = str(team["team"]["id"])
            if tid in seen:
                raise ValueError(f"Duplicate conference membership: {year}/{tid}")
            seen.add(tid)
            if tid not in identities:
                unmatched.append({"team_id": tid, "name": team["team"].get("displayName"), "conference": label})
                continue
            if (year, tid) in EXCLUSIONS:
                text, source = EXCLUSIONS[year, tid]
                result[identities[tid]] = {"regular_season_result": text, "regular_season_standings": {"conference": label, "conference_id": cid, "final": final, "rank": None, "status": "excluded_from_standings", "source": source}}
                continue
            w, l = records[tid]
            details = {"conference": label, "conference_id": cid, "wins": w, "losses": l, "final": final, "ranking_basis": basis}
            if not w + l:
                text = "No conference games played (0–0)" if final else "Conference play not started (0–0)"
                details.update(rank=None, tied=False)
            else:
                rank = 1 + sum(v > ratios[tid] for v in ratios.values())
                tied = sum(v == ratios[tid] for v in ratios.values()) > 1
                details.update(rank=rank, tied=tied)
                text = (("Tied for " if tied else "Finished ") if final else ("Currently tied for " if tied else "Currently "))
                text += f"{ordinal(rank)} in the {label} ({w}–{l})"
                if final and tid in winners:
                    championship = "Regular-Season Co-Champion" if len(winners) > 1 else "Regular-Season Champion"
                    details["championship"] = championship
                    text += " — " + championship
                division = title_info.get("division_champions", {}).get(tid)
                if final and division:
                    details["division_championship"] = division
                    text += " — " + division
            result[identities[tid]] = {"regular_season_result": text, "regular_season_standings": details}
    if len(seen) < 300 or len(data.get("children", [])) < 30:
        raise ValueError(f"Incomplete Division I standings: {len(seen)} teams")
    return result, unmatched


def load_source(year, directory=None):
    if directory:
        return json.loads((directory / f"{year}.json").read_text())
    req = Request(SOURCE.format(year=year), headers={"User-Agent": "BetWiseResearch/1.0"})
    with urlopen(req, timeout=45) as response:
        return json.load(response)


def apply_membership_exceptions(season, year, rules):
    for slug, info in rules.get("program_starts", {}).items():
        if year < info["first_conference_season"]:
            if slug in season:
                raise ValueError(f"Membership exception conflicts with standings: {year}/{slug}")
            season[slug] = {"regular_season_result": "Not a Division I conference member this season", "regular_season_standings": {"final": True, "rank": None, "status": "not_division_i", "source": info["source"]}}
    for slug, info in rules.get("canceled_team_seasons", {}).get(str(year), {}).items():
        if slug in season:
            raise ValueError(f"Cancellation conflicts with standings: {year}/{slug}")
        season[slug] = {"regular_season_result": "Season canceled (COVID-19) — No conference standings", "regular_season_standings": {"conference": info["conference"], "final": True, "rank": None, "status": "season_canceled", "source": info["source"]}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", nargs="+", type=int, help="Explicit historical seasons to backfill (ending years)")
    parser.add_argument("--source-dir", type=Path)
    args = parser.parse_args()
    current = active_year()
    years = args.years or [current]
    path = ROOT / "data/cbb/conference-tournament-results.json"
    db = json.loads(path.read_text())
    registry = json.loads((ROOT / "data/sports/team-registry.json").read_text())["teams"]
    identities = {str(t["espn_id"]): t["slug"] for t in registry if t["sport"] == "cbb"}
    title_path = ROOT / "data/cbb/regular-season-championships.json"
    rules = json.loads(title_path.read_text())
    titles = rules["seasons"]
    reports = {}
    for year in years:
        data = load_source(year, args.source_dir)
        now = datetime.now(ZoneInfo("America/New_York"))
        final = year < current or (year == current and now.month in (4, 5, 6) and (now.month > 4 or now.day >= 10))
        season, unmatched = make_season(data, year, identities, titles, final)
        apply_membership_exceptions(season, year, rules)
        missing = sorted(set(identities.values()) - season.keys())
        if missing:
            raise ValueError(f"Unresolved registered team seasons: {year}: {missing}")
        saved = db.setdefault("seasons", {}).setdefault(str(year), {})
        for slug, fields in season.items():
            saved.setdefault(slug, {}).update(fields)
        db.setdefault("regular_season_sources", {})[str(year)] = {
            "standings": SOURCE.format(year=year),
            "championships": "data/cbb/regular-season-championships.json",
            "season": data["season"].get("displayName"),
        }
        reports[str(year)] = {"published": len(season), "unmatched_source_teams": unmatched}
        print(year, "conference finishes:", len(season), "unmatched historical schools:", len(unmatched))
    path.write_text(json.dumps(db, ensure_ascii=False, separators=(",", ":")) + "\n")
    # A report for this run is logged, not used as a false claim of all-season completeness.
    print(json.dumps(reports, ensure_ascii=False))


if __name__ == "__main__":
    main()
