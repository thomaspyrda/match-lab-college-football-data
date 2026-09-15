import json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class AdvancedProfileTests(unittest.TestCase):
    def test_profiles_are_pregame_and_bounded(self):
        files = sorted((ROOT / "data" / "profiles").glob("*.json"))
        self.assertTrue(files, "advanced profile files are missing")
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(data["pregame_only"])
            self.assertEqual(data["schema_version"], "2.1")
            populated = 0
            for week, board in data["weeks"].items():
                self.assertEqual(board["through_week"], max(0, int(week) - 1))
                for profile in board.get("teams", {}).values():
                    for key, score in profile.items():
                        if key in ("games_played", "metrics_available") or score is None:
                            continue
                        self.assertGreaterEqual(score, 1)
                        self.assertLessEqual(score, 100)
                    populated += profile.get("metrics_available", 0)
            if int(data["season"]) < 2026:
                self.assertGreater(populated, 0, f"{path.name} contains no advanced metric values")

    def test_game_profiles_never_use_current_week(self):
        for path in sorted((ROOT / "data" / "historical").glob("*.json")):
            for game in json.loads(path.read_text(encoding="utf-8")).get("games", []):
                for side in ("home_profile", "away_profile"):
                    advanced = game.get(side, {}).get("advanced")
                    if advanced:
                        self.assertEqual(advanced.get("through_week"), max(0, game["week"] - 1))

    def test_recent_form_uses_every_prior_season_game(self):
        for path in sorted((ROOT / "data" / "historical").glob("*.json")):
            prior_games = {}
            games = json.loads(path.read_text(encoding="utf-8")).get("games", [])
            for game in sorted(games, key=lambda item: item.get("start_date") or ""):
                for team, side in ((game["home"], "home_profile"), (game["away"], "away_profile")):
                    actual = game.get(side, {}).get("recent_form", {}).get("games")
                    self.assertEqual(actual, prior_games.get(team, 0), f"{path.name}: {team} before {game['game_id']}")
                if game.get("result") is not None:
                    prior_games[game["home"]] = prior_games.get(game["home"], 0) + 1
                    prior_games[game["away"]] = prior_games.get(game["away"], 0) + 1

    def test_browser_requests_ten_closest_matches(self):
        source = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn(".slice(0,10)", source)

if __name__ == "__main__":
    unittest.main()
