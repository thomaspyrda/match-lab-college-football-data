import unittest
from validate_nba_historical_lines import find_game, grade

class NBALineBackfillTests(unittest.TestCase):
    def test_2015_opening_night_atlanta_pistons(self):
        game=find_game("atlanta-hawks", 2016, "0021500001")
        # Public historical quote verified on StatMuse; this is not TeamRankings-derived.
        quote={
            "game_id":"0021500001",
            "source":"StatMuse",
            "source_url":"https://www.statmuse.com/nba/ask/hawks-regular-season-and-playoffs-over-and-under-record-vs-pistons",
            "line_type":"published_unspecified",
            "team_spread":-6.5,
            "total":197.5,
        }
        result=grade(game,quote)
        self.assertEqual((result["ats"],result["ou"]),("L","Over"))
        self.assertEqual((game["score_for"],game["score_against"]),(94,106))
        self.assertEqual(result["line_type"],"published_unspecified")

if __name__=="__main__":
    unittest.main()
