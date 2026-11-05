import copy
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from nba_market_quotes import current_market
import refresh_afternoon_pregame as pregame


class QuoteTests(unittest.TestCase):
    def event(self, quotes=None):
        return {"id": "123", "status": {"type": {"completed": False, "description": "Scheduled"}},
                "competitions": [{"competitors": [
                    {"homeAway": "home", "team": {"abbreviation": "PHX"}},
                    {"homeAway": "away", "team": {"abbreviation": "ORL"}}],
                    "odds": quotes or []}]}

    def modern(self):
        return {"provider": {"name": "Book"}, "pointSpread": {
            "home": {"close": {"line": "-3.5"}}, "away": {"close": {"line": "+3.5"}}},
            "total": {"over": {"close": {"line": "o224.5"}},
                      "under": {"close": {"line": "u224.5"}}}}

    def test_legacy_scoreboard_does_not_request_summary(self):
        event = self.event([{"details": "PHX -4.5", "overUnder": 223, "provider": {"name": "Book"}}])
        with patch("builtins.print"):
            quote = current_market(event, "now", lambda _: self.fail("Unnecessary summary request"))
        self.assertEqual((quote["spread"], quote["total"]), ("PHX -4.5", 223))

    def test_empty_scoreboard_uses_modern_summary(self):
        called = []
        def summary(gid):
            called.append(gid)
            return {"pickcenter": [self.modern()]}
        quote = current_market(self.event(), "now", summary)
        self.assertEqual(called, ["123"])
        self.assertEqual(quote, dict(spread="PHX -3.5", total=224.5, provider="Book", observed_at="now"))

    def test_current_quote_precedes_close_and_away_favorite(self):
        q = self.modern()
        q["pointSpread"]["home"]["current"] = {"line": "+2"}
        q["pointSpread"]["away"]["current"] = {"line": "-2"}
        quote = current_market(self.event([q]), "now")
        self.assertEqual(quote["spread"], "ORL -2")

    def test_partial_scoreboard_uses_complete_summary(self):
        quote = current_market(self.event([{"overUnder": 220}]), "now",
                               lambda _: {"pickcenter": [self.modern()]})
        self.assertEqual((quote["spread"], quote["total"]), ("PHX -3.5", 224.5))

    def test_no_quote_is_not_an_invented_current_line(self):
        quote = current_market(self.event(), "now", lambda _: {})
        self.assertTrue(all(value is None for value in quote.values()))
        quote = current_market(self.event([{"spread": 5, "overUnder": "NaN"}]), "now")
        self.assertIsNone(quote["spread"])
        self.assertIsNone(quote["observed_at"])

    def test_pickem_is_zero_and_conflicting_totals_are_unavailable(self):
        q = self.modern()
        q["pointSpread"] = {"home": {"close": {"line": "PK"}}, "away": {"close": {"line": "PK"}}}
        q["total"]["under"]["close"]["line"] = "u225.5"
        quote = current_market(self.event([q]), "now")
        self.assertEqual(quote["spread"], "PK")
        self.assertIsNone(quote["total"])

    def test_nba_pregame_fallback_preserves_statistics_and_final_games(self):
        final = {"id": "final", "status": "Final", "market": {"total": 150}}
        upcoming = {"id": "123", "stats": {"ppg": 100}, "rank": 12, "market": {"total": 140}}
        snapshot = {"games": [final, upcoming], "updated_at": "original-stats-time"}
        original = copy.deepcopy(snapshot)
        event = self.event()
        def source(url):
            return {"pickcenter": [self.modern()]} if "summary?" in url else {"events": [event]}
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "dashboard.json"
            path.write_text(json.dumps(snapshot))
            with patch.object(pregame, "ROOT", root), patch.object(pregame, "request", side_effect=source), \
                 patch.object(pregame, "refresh_availability"):
                pregame.refresh("nba", "basketball/nba", "dashboard.json")
            after = json.loads(path.read_text())
        self.assertEqual(after["games"][0], original["games"][0])
        self.assertEqual(after["updated_at"], original["updated_at"])
        self.assertEqual(after["games"][1]["stats"], upcoming["stats"])
        self.assertEqual(after["games"][1]["rank"], 12)
        self.assertEqual(after["games"][1]["market"]["spread"], "PHX -3.5")
