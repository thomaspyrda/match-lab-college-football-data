from cfb_dashboard.pipeline.pregame import eligible_completed_games, record_before_week


GAMES = [
    {"season": 2026, "week": 1, "completed": True, "homeTeam": "A", "awayTeam": "B", "homePoints": 28, "awayPoints": 14},
    {"season": 2026, "week": 2, "completed": True, "homeTeam": "C", "awayTeam": "A", "homePoints": 10, "awayPoints": 17},
    {"season": 2026, "week": 3, "completed": True, "homeTeam": "A", "awayTeam": "D", "homePoints": 7, "awayPoints": 21},
    {"season": 2026, "week": 4, "completed": False, "homeTeam": "A", "awayTeam": "E", "homePoints": None, "awayPoints": None},
]


def test_week_three_excludes_week_three_and_future():
    rows = eligible_completed_games(GAMES, 2026, 3)
    assert [g["week"] for g in rows] == [1, 2]


def test_record_is_pregame_safe():
    assert record_before_week(GAMES, "A", 2026, 3)["display"] == "2-0"
    assert record_before_week(GAMES, "A", 2026, 4)["display"] == "2-1"
