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
            for week, board in data["weeks"].items():
                self.assertEqual(board["through_week"], max(0, int(week) - 1))
                for profile in board.get("teams", {}).values():
                    for key, score in profile.items():
                        if key in ("games_played", "metrics_available") or score is None:
                            continue
                        self.assertGreaterEqual(score, 1)
                        self.assertLessEqual(score, 100)

    def test_game_profiles_never_use_current_week(self):
        for path in sorted((ROOT / "data" / "historical").glob("*.json")):
            for game in json.loads(path.read_text(encoding="utf-8")).get("games", []):
                for side in ("home_profile", "away_profile"):
                    advanced = game.get(side, {}).get("advanced")
                    if advanced:
                        self.assertEqual(advanced.get("through_week"), max(0, game["week"] - 1))

if __name__ == "__main__":
    unittest.main()
