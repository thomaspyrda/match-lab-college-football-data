import unittest

from build_ap_elo import ap_by_week, rank_elos, weekly_elo_boards


class BuildTests(unittest.TestCase):
    def test_ap_requires_complete_top_25(self):
        payload = [{"season": 2024, "week": 2, "polls": [{
            "poll": "AP Top 25", "ranks": [{"rank": i, "school": f"T{i}"} for i in range(1, 25)]
        }]}]
        with self.assertRaises(ValueError):
            ap_by_week(payload)

    def test_elo_rank_is_deterministic_with_ties(self):
        board = rank_elos({"B": 1600, "A": 1600, "C": 1500}, 3)
        self.assertEqual(board["A"]["rank"], 1)
        self.assertEqual(board["B"]["rank"], 1)
        self.assertEqual(board["C"]["rank"], 3)

    def test_bye_week_uses_next_verified_pregame_elo(self):
        roster = [{"school": "A"}, {"school": "B"}]
        games = [{
            "week": 1, "startDate": "2024-08-31T12:00:00Z",
            "homeTeam": "A", "homePregameElo": 1500, "homePostgameElo": 1512,
            "awayTeam": "B", "awayPregameElo": 1500, "awayPostgameElo": 1488,
        }, {
            "week": 3, "startDate": "2024-09-14T12:00:00Z",
            "homeTeam": "A", "homePregameElo": 1512, "homePostgameElo": 1520,
            "awayTeam": "B", "awayPregameElo": 1488, "awayPostgameElo": 1480,
        }]
        boards = weekly_elo_boards(roster, games, [1, 2, 3])
        self.assertEqual(boards[1]["A"]["rating"], 1500)
        self.assertEqual(boards[2]["A"]["rating"], 1512)
        self.assertEqual(boards[3]["A"]["rating"], 1512)

    def test_ap_allows_official_tie_at_25(self):
        ranks = [{"rank": i, "school": f"T{i}"} for i in range(1, 26)]
        ranks.append({"rank": 25, "school": "T25b"})
        payload = [{"season": 2019, "week": 2, "polls": [{"poll": "AP Top 25", "ranks": ranks}]}]
        self.assertEqual(len(ap_by_week(payload)[2]), 26)


if __name__ == "__main__":
    unittest.main()
