#!/usr/bin/env python3
"""Build frozen NBA team rankings from the archived regular-season team tables."""
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "nba/teams/data"
OUTPUT = ROOT / "nba/rankings/data/nba-team-rankings.json"

TEAM_INFO = {
    "atlanta-hawks": ("Atlanta Hawks", "ATL", "Eastern", "Southeast"),
    "boston-celtics": ("Boston Celtics", "BOS", "Eastern", "Atlantic"),
    "brooklyn-nets": ("Brooklyn Nets", "BKN", "Eastern", "Atlantic"),
    "charlotte-hornets": ("Charlotte Hornets", "CHA", "Eastern", "Southeast"),
    "chicago-bulls": ("Chicago Bulls", "CHI", "Eastern", "Central"),
    "cleveland-cavaliers": ("Cleveland Cavaliers", "CLE", "Eastern", "Central"),
    "dallas-mavericks": ("Dallas Mavericks", "DAL", "Western", "Southwest"),
    "denver-nuggets": ("Denver Nuggets", "DEN", "Western", "Northwest"),
    "detroit-pistons": ("Detroit Pistons", "DET", "Eastern", "Central"),
    "golden-state-warriors": ("Golden State Warriors", "GSW", "Western", "Pacific"),
    "houston-rockets": ("Houston Rockets", "HOU", "Western", "Southwest"),
    "indiana-pacers": ("Indiana Pacers", "IND", "Eastern", "Central"),
    "la-clippers": ("LA Clippers", "LAC", "Western", "Pacific"),
    "los-angeles-lakers": ("Los Angeles Lakers", "LAL", "Western", "Pacific"),
    "memphis-grizzlies": ("Memphis Grizzlies", "MEM", "Western", "Southwest"),
    "miami-heat": ("Miami Heat", "MIA", "Eastern", "Southeast"),
    "milwaukee-bucks": ("Milwaukee Bucks", "MIL", "Eastern", "Central"),
    "minnesota-timberwolves": ("Minnesota Timberwolves", "MIN", "Western", "Northwest"),
    "new-orleans-pelicans": ("New Orleans Pelicans", "NOP", "Western", "Southwest"),
    "new-york-knicks": ("New York Knicks", "NYK", "Eastern", "Atlantic"),
    "oklahoma-city-thunder": ("Oklahoma City Thunder", "OKC", "Western", "Northwest"),
    "orlando-magic": ("Orlando Magic", "ORL", "Eastern", "Southeast"),
    "philadelphia-76ers": ("Philadelphia 76ers", "PHI", "Eastern", "Atlantic"),
    "phoenix-suns": ("Phoenix Suns", "PHX", "Western", "Pacific"),
    "portland-trail-blazers": ("Portland Trail Blazers", "POR", "Western", "Northwest"),
    "sacramento-kings": ("Sacramento Kings", "SAC", "Western", "Pacific"),
    "san-antonio-spurs": ("San Antonio Spurs", "SAS", "Western", "Southwest"),
    "toronto-raptors": ("Toronto Raptors", "TOR", "Eastern", "Atlantic"),
    "utah-jazz": ("Utah Jazz", "UTA", "Western", "Northwest"),
    "washington-wizards": ("Washington Wizards", "WAS", "Eastern", "Southeast"),
}
RAW_TO_METRICS = {
    "ast": "assists_per_game", "tov": "turnovers_per_game",
    "trb": "rebounds_per_game", "stl": "steals_per_game",
    "blk": "blocks_per_game", "opp_ast": "opponent_assists_per_game",
    "opp_tov": "opponent_turnovers_per_game", "opp_trb": "rebounds_allowed_per_game",
    "opp_stl": "opponent_steals_per_game", "opp_blk": "opponent_blocks_per_game",
}
METRIC_LABELS = {
    "ppg": "Points per game", "ppg_home": "Points per game at home",
    "ppg_away": "Points per game away", "ppg_allowed": "Points allowed per game",
    "ppg_allowed_home": "Points allowed per game at home",
    "ppg_allowed_away": "Points allowed per game away",
    "fg_pct": "Field goal percentage", "opp_fg_pct": "Opponent field goal percentage",
    "three_pct": "Three point percentage", "opp_three_pct": "Opponent three point percentage",
    "assists_per_game": "Assists per game", "turnovers_per_game": "Turnovers per game",
    "turnover_margin": "Turnover margin per game", "pace": "Pace",
    "rebounds_per_game": "Rebounds per game",
    "rebounds_allowed_per_game": "Rebounds allowed per game",
    "offensive_rebound_rate": "Offensive rebound rate",
    "defensive_rebound_rate": "Defensive rebound rate",
    "ortg": "Offensive rating", "drtg": "Defensive rating",
    "net_rating": "Net rating", "overall_rating": "Overall rating",
    "offense_rating": "Offense rating", "defense_rating": "Defense rating",
    "efg_pct": "Effective field goal percentage",
    "opp_efg_pct": "Opponent effective field goal percentage",
    "ts_pct": "True shooting percentage", "ft_pct": "Free throw percentage",
    "three_attempt_rate": "Three point attempt rate",
    "ft_rate": "Free throw rate", "ft_made_rate": "Free throws made per field goal attempt",
    "tov_pct": "Turnover percentage", "opp_tov_pct": "Opponent turnover percentage",
    "steals_per_game": "Steals per game", "blocks_per_game": "Blocks per game",
    "opponent_assists_per_game": "Opponent assists per game",
    "opponent_turnovers_per_game": "Opponent turnovers per game",
    "opponent_steals_per_game": "Opponent steals per game",
    "opponent_blocks_per_game": "Opponent blocks per game",
    "rim_fg_pct": "At rim field goal percentage",
    "opp_rim_fg_pct": "Opponent at rim field goal percentage",
}
LOWER_IS_BETTER = {
    "ppg_allowed", "ppg_allowed_home", "ppg_allowed_away",
    "opp_fg_pct", "opp_three_pct", "turnovers_per_game",
    "rebounds_allowed_per_game", "drtg", "opponent_assists_per_game",
    "opponent_steals_per_game", "opponent_blocks_per_game",
    "opp_efg_pct", "opp_rim_fg_pct", "tov_pct",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def num(value):
    if value is None or value == "":
        return None
    try:
        value = float(str(value).replace(",", "").replace("%", ""))
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def avg(values):
    values = [v for v in values if v is not None]
    return statistics.mean(values) if values else None


def rate(value, games):
    return round(value / games, 2) if value is not None and games else None


def make_ranks(rows, key, higher_is_better=True):
    ordered = sorted(
        rows,
        key=lambda row: row["metrics"].get(key) if row["metrics"].get(key) is not None else (-math.inf if higher_is_better else math.inf),
        reverse=higher_is_better,
    )
    ranks = {}
    previous = object()
    for position, row in enumerate(ordered, 1):
        value = row["metrics"].get(key)
        comparison = round(value, 8) if value is not None else None
        if position == 1 or comparison != previous:
            rank = position
        ranks[row["slug"]] = rank
        previous = comparison
    return ranks


def main():
    archive = {}
    details = {}
    for slug in TEAM_INFO:
        archive_path = DATA_DIR / f"{slug}.json"
        detail_path = DATA_DIR / f"{slug}-season-details.json"
        if not archive_path.exists() or not detail_path.exists():
            raise FileNotFoundError(f"Missing NBA source archive for {slug}")
        archive[slug] = read_json(archive_path).get("seasons", [])
        details[slug] = read_json(detail_path).get("seasons", {})

    year_sets = [
        {str(season.get("key")) for season in archive[slug]}
        & {str(year) for year in details[slug]}
        for slug in TEAM_INFO
    ]
    years = sorted(set.intersection(*year_sets), key=int)
    required_history = {str(year) for year in range(2016, 2027)}
    if not required_history.issubset(set(years)):
        raise ValueError("Expected archived seasons 2015–16 through 2025–26 for all 30 teams")
    output = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Basketball-Reference NBA regular-season team tables and archived schedules",
        "methodology": {
            "scope": "NBA only; all 30 franchises; regular-season team performance",
            "overall": "Net rating = offensive rating minus defensive rating; no opponent-strength adjustment.",
            "offense": "Offensive rating in points per 100 estimated possessions, centered on that season's 30-team average.",
            "defense": "Defensive strength is that season's 30-team average defensive rating minus the team's defensive rating.",
            "overall_rating": "Net rating centered on the 30-team season average; positive is above average, negative is below average.",
            "standard_deviation": "Rating divided by the population standard deviation across the 30 teams for that season.",
            "home_away": "Home and away scoring splits use archived regular-season game results; neutral-site games are excluded.",
        },
        "metric_labels": METRIC_LABELS,
        "lower_is_better": sorted(LOWER_IS_BETTER),
        "seasons": {},
    }

    for year in years:
        rows = []
        season_label = None
        for slug, (name, abbr, conference, division) in TEAM_INFO.items():
            team_season = next((s for s in archive[slug] if str(s.get("key")) == year), None)
            detail = details[slug].get(year)
            if not team_season or not detail:
                raise ValueError(f"Missing {year} season data for {slug}")
            season_label = team_season.get("label", season_label)
            metrics = dict(team_season.get("metrics") or {})
            raw = team_season.get("raw_tables") or {}
            per_game = raw.get("per_game") or {}
            opponent = raw.get("opponent_per_game") or {}
            advanced = raw.get("advanced") or {}

            for raw_key, metric_key in RAW_TO_METRICS.items():
                source_table = opponent if raw_key.startswith("opp_") else per_game
                metrics[metric_key] = num(source_table.get(raw_key))
            metrics["fg_pct"] = num(metrics.get("fg_pct"))
            metrics["opp_fg_pct"] = num(metrics.get("opp_fg_pct"))
            metrics["three_pct"] = num(metrics.get("three_pct"))
            metrics["opp_three_pct"] = num(metrics.get("opp_three_pct"))
            metrics["offensive_rebound_rate"] = num(metrics.get("orb_pct"))
            metrics["defensive_rebound_rate"] = num(metrics.get("drb_pct"))
            metrics["turnover_margin"] = round(
                (metrics.get("opponent_turnovers_per_game") or 0) - (metrics.get("turnovers_per_game") or 0), 2
            )
            metrics["pace"] = num(metrics.get("pace") or advanced.get("pace"))
            metrics["ortg"] = num(metrics.get("ortg") or advanced.get("off_rtg"))
            metrics["drtg"] = num(metrics.get("drtg") or advanced.get("def_rtg"))
            metrics["net_rating"] = num(metrics.get("net_rating") or advanced.get("net_rtg"))
            metrics["ppg"] = num(metrics.get("ppg"))
            metrics["ppg_allowed"] = num(metrics.get("points_allowed_per_game"))
            metrics["points_allowed_per_game"] = metrics["ppg_allowed"]
            metrics["ppg_home"] = metrics["ppg_away"] = None
            metrics["ppg_allowed_home"] = metrics["ppg_allowed_away"] = None
            home_for, home_against, home_count = 0, 0, 0
            away_for, away_against, away_count = 0, 0, 0
            for game in detail.get("games", []):
                if game.get("neutral"):
                    continue
                score_for, score_against = num(game.get("score_for")), num(game.get("score_against"))
                if score_for is None or score_against is None:
                    continue
                if game.get("location") == "Home":
                    home_for += score_for
                    home_against += score_against
                    home_count += 1
                elif game.get("location") == "Away":
                    away_for += score_for
                    away_against += score_against
                    away_count += 1
            if home_count:
                metrics["ppg_home"] = round(home_for / home_count, 2)
                metrics["ppg_allowed_home"] = round(home_against / home_count, 2)
            if away_count:
                metrics["ppg_away"] = round(away_for / away_count, 2)
                metrics["ppg_allowed_away"] = round(away_against / away_count, 2)

            for key in ("efg_pct", "ts_pct", "ft_pct", "three_attempt_rate", "ft_rate",
                        "ft_made_rate", "tov_pct", "opp_tov_pct", "rim_fg_pct", "opp_rim_fg_pct"):
                metrics[key] = num(metrics.get(key))
            record = team_season.get("record")
            if isinstance(record, dict):
                record = record.get("overall")
            rows.append({
                "slug": slug,
                "team": name,
                "abbreviation": abbr,
                "conference": conference,
                "division": division,
                "logo": f"https://a.espncdn.com/i/teamlogos/nba/500/{abbr.lower()}.png",
                "record": record or detail.get("record"),
                "games_played": int(num(team_season.get("games_played")) or detail.get("games_played") or 0),
                "metrics": metrics,
                "ratings": {},
                "ranks": {},
            })

        league_ortg = avg([r["metrics"].get("ortg") for r in rows])
        league_drtg = avg([r["metrics"].get("drtg") for r in rows])
        league_net = avg([r["metrics"].get("net_rating") for r in rows])
        for row in rows:
            m = row["metrics"]
            m["offense_rating"] = round(m["ortg"] - league_ortg, 4) if m.get("ortg") is not None else None
            m["defense_rating"] = round(league_drtg - m["drtg"], 4) if m.get("drtg") is not None else None
            m["overall_rating"] = round(m["net_rating"] - league_net, 4) if m.get("net_rating") is not None else None
            row["ratings"] = {
                "overall": m["overall_rating"],
                "offense": m["offense_rating"],
                "defense": m["defense_rating"],
                "overall_sd": None, "offense_sd": None, "defense_sd": None,
            }

        overall_sd = statistics.pstdev([r["metrics"]["overall_rating"] for r in rows])
        offense_sd = statistics.pstdev([r["metrics"]["offense_rating"] for r in rows])
        defense_sd = statistics.pstdev([r["metrics"]["defense_rating"] for r in rows])
        for row in rows:
            r = row["ratings"]
            r["overall_sd"] = round(r["overall"] / overall_sd, 3) if overall_sd else 0
            r["offense_sd"] = round(r["offense"] / offense_sd, 3) if offense_sd else 0
            r["defense_sd"] = round(r["defense"] / defense_sd, 3) if defense_sd else 0

        rank_defs = {
            "overall": ("overall_rating", True), "offense": ("offense_rating", True),
            "defense": ("defense_rating", True),
        }
        for rank_name, (metric, higher) in rank_defs.items():
            ranks = make_ranks(rows, metric, higher)
            for row in rows:
                row["ranks"][rank_name] = ranks[row["slug"]]
        for row in rows:
            row["metrics"].pop("points_allowed_per_game", None)

        output["seasons"][year] = {
            "label": season_label or year,
            "status": "in_progress" if int(year) == datetime.now(timezone.utc).year + 1 else "complete",
            "team_count": len(rows),
            "league_average": {
                "offensive_rating": round(league_ortg, 3),
                "defensive_rating": round(league_drtg, 3),
                "net_rating": round(league_net, 3),
            },
            "source_url": f"https://www.basketball-reference.com/leagues/NBA_{year}.html",
            "teams": sorted(rows, key=lambda row: row["ranks"]["overall"]),
        }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, separators=(",", ":"), ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(output['seasons'])} seasons / {sum(s['team_count'] for s in output['seasons'].values())} team-seasons to {OUTPUT}")


if __name__ == "__main__":
    main()
