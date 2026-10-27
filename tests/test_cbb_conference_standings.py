import unittest
from datetime import datetime

from backfill_cbb_conference_standings import active_year, apply_membership_exceptions, make_season


def entry(tid, wins, losses, overall=99, seed=1):
    return {"team": {"id": str(tid)}, "stats": [
        {"type": "wins", "name": "wins", "value": overall},
        {"type": "home_wins", "name": "wins", "value": 88},
        {"type": "vsconf_wins", "name": "wins", "value": wins},
        {"type": "vsconf_losses", "name": "losses", "value": losses},
        {"type": "playoffseed", "value": seed},
    ]}


def fixture(year=2025):
    group = {"id": "2", "name": "ACC", "standings": {"entries": [
        entry("a", 15, 3, overall=15, seed=2),
        entry("b", 15, 3, overall=30, seed=1),
        entry("c", 12, 6, overall=40, seed=3),
    ]}}
    # Include a complete-size league response so the production coverage guard
    # remains exercised rather than disabled for tests.
    groups = [group] + [{"id": str(i + 100), "name": "Other", "standings": {"entries": [
        entry(f"{i}-{j}", j + 1, 10 - j) for j in range(11)
    ]}} for i in range(29)]
    return {"season": {"year": year}, "children": groups}


class ConferenceStandingsTests(unittest.TestCase):
    def test_conference_records_and_shared_titles_ignore_overall_record_and_seed(self):
        titles = {"2025": {"2": {"champions": ["a", "b"]}}}
        result, _ = make_season(fixture(), 2025, {"a": "school-a", "b": "school-b", "c": "school-c"}, titles)
        self.assertEqual(result["school-a"]["regular_season_result"], "Tied for 1st in the ACC (15–3) — Regular-Season Co-Champion")
        self.assertEqual(result["school-b"]["regular_season_standings"]["rank"], 1)
        self.assertEqual(result["school-c"]["regular_season_result"], "Finished 3rd in the ACC (12–6)")

    def test_first_place_does_not_invent_a_championship(self):
        result, _ = make_season(fixture(), 2025, {"a": "a"}, {})
        self.assertNotIn("Champion", result["a"]["regular_season_result"])

    def test_unbalanced_seasons_use_sourced_wins_rule(self):
        data = fixture(2021)
        data["children"][0]["standings"]["entries"] = [entry("a", 12, 4), entry("b", 12, 6)]
        titles = {"2021": {"2": {"champions": ["a", "b"], "ranking_basis": "conference_wins"}}}
        result, _ = make_season(data, 2021, {"a": "a", "b": "b"}, titles)
        self.assertIn("Tied for 1st", result["b"]["regular_season_result"])
        self.assertIn("Co-Champion", result["b"]["regular_season_result"])

    def test_exact_win_percentages_for_unequal_schedules(self):
        data = fixture()
        data["children"][0]["standings"]["entries"] = [entry("a", 2, 1), entry("b", 4, 2), entry("c", 5, 3)]
        result, _ = make_season(data, 2025, {"a": "a", "b": "b", "c": "c"}, {})
        self.assertTrue(result["a"]["regular_season_standings"]["tied"])
        self.assertEqual(result["c"]["regular_season_standings"]["rank"], 3)

    def test_current_preseason_has_no_finish_or_championship(self):
        data = fixture(2027)
        data["children"][0]["standings"]["entries"] = [entry("a", 0, 0)]
        result, _ = make_season(data, 2027, {"a": "a"}, {}, final=False)
        self.assertEqual(result["a"]["regular_season_result"], "Conference play not started (0–0)")
        self.assertIsNone(result["a"]["regular_season_standings"]["rank"])

    def test_invalid_or_incomplete_responses_are_rejected(self):
        with self.assertRaises(ValueError):
            make_season(fixture(), 2024, {}, {})
        data = fixture()
        data["children"] = data["children"][:2]
        with self.assertRaises(ValueError):
            make_season(data, 2025, {}, {})
        data = fixture()
        data["children"][0]["standings"]["entries"][0]["stats"] = []
        with self.assertRaises(ValueError):
            make_season(data, 2025, {}, {})

    def test_season_year_rollover(self):
        self.assertEqual(active_year(datetime(2026, 6, 30)), 2026)
        self.assertEqual(active_year(datetime(2026, 7, 1)), 2027)

    def test_membership_and_cancellations_do_not_invent_records(self):
        rules = {"program_starts": {"new-program": {"first_conference_season": 2023, "source": "membership-source"}}, "canceled_team_seasons": {"2021": {"opted-out": {"conference": "MEAC", "source": "cancellation-source"}}}}
        season = {}
        apply_membership_exceptions(season, 2021, rules)
        self.assertEqual(season["new-program"]["regular_season_standings"]["status"], "not_division_i")
        self.assertEqual(season["opted-out"]["regular_season_standings"]["status"], "season_canceled")
        self.assertNotIn("wins", season["opted-out"]["regular_season_standings"])
        with self.assertRaises(ValueError):
            apply_membership_exceptions({"new-program": {}}, 2021, rules)


if __name__ == "__main__":
    unittest.main()
