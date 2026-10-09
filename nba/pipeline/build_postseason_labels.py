"""Refresh the browser's inline playoff labels from the sourced postseason archive."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "nba/teams/data/postseason-results.json"
SCRIPT = ROOT / "nba/teams/nfl-style.js"


def main():
    archive = json.loads(DATA.read_text())
    labels = {}
    for year, season in archive["seasons"].items():
        teams, series = season["teams"], season["series"]
        assert len(teams) == 30 and len(series) == 15
        assert sum(t["status"] == "champion" for t in teams.values()) == 1
        assert sum(t["status"] == "series_elimination" for t in teams.values()) == 15
        assert len({s["loser"] for s in series}) == 15
        previous = None
        for rnd, count in [("First Round", 8), ("Conference Semifinals", 4), ("Conference Finals", 2), ("NBA Finals", 1)]:
            rows = [s for s in series if s["round"] == rnd]
            assert len(rows) == count
            participants = {team for s in rows for team in (s["winner"], s["loser"])}
            assert len(participants) == count * 2
            if previous is not None:
                assert participants == previous
            previous = {s["winner"] for s in rows}
            for row in rows:
                assert row["winner_wins"] == 4 and 0 <= row["loser_wins"] <= 3
                loser = teams[row["loser"]]
                assert loser["opponent"] == row["winner"]
                assert loser["team_series_wins"] == row["loser_wins"]
        labels[year] = {slug: row["label"] for slug, row in teams.items()}
    payload = json.dumps(labels, separators=(",", ":"), ensure_ascii=False)
    pattern = r"/\* NBA_POSTSEASON_START \*/.*?/\* NBA_POSTSEASON_END \*/"
    replacement = "/* NBA_POSTSEASON_START */const playoffResults=" + payload + ";/* NBA_POSTSEASON_END */"
    script, count = re.subn(pattern, lambda _: replacement, SCRIPT.read_text(), count=1, flags=re.S)
    assert count == 1, "Postseason cache markers missing"
    SCRIPT.write_text(script)
    print(f"Verified and refreshed {sum(map(len, labels.values()))} postseason labels")


if __name__ == "__main__":
    main()