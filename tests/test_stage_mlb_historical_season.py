import unittest
from stage_mlb_historical_season import stage_season

def crosswalk():
    return {"teams":{str(i):{"slug":f"team-{i}"} for i in range(1,31)}}

def fixture(url):
    return {"dates":[{"games":[{"gamePk":10,"gameType":"R","officialDate":"2020-08-01",
       "status":{"abstractGameState":"Final"},"teams":{"home":{"team":{"id":1},"score":3},
       "away":{"team":{"id":2},"score":2}}},{"gamePk":11,"gameType":"W",
       "officialDate":"2020-10-20","status":{"abstractGameState":"Final"},
       "teams":{"home":{"team":{"id":1},"score":1},"away":{"team":{"id":2},"score":4}}}]}]}
class HistoricalStageTests(unittest.TestCase):
    def test_result_and_postseason_separation(self):
        r=stage_season(2020,crosswalk(),fixture)
        self.assertEqual(r["coverage"]["regular_games"],1)
        self.assertEqual(r["coverage"]["postseason_games"],1)
        self.assertEqual(r["coverage"]["expected_games_per_team"],60)
        self.assertEqual(r["games"]["10"]["player_data_coverage"],"not_loaded")
    def test_duplicate_rejected(self):
        def repeated(url):
            r=fixture(url)
            r["dates"][0]["games"].append(dict(r["dates"][0]["games"][0]))
            return r
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            stage_season(2020,crosswalk(),repeated)
    def test_invalid_score_rejected(self):
        def invalid(url):
            r=fixture(url)
            r["dates"][0]["games"][0]["teams"]["home"]["score"]=-1
            return r
        with self.assertRaisesRegex(ValueError,"Invalid"):
            stage_season(2020,crosswalk(),invalid)
if __name__=="__main__":
    unittest.main()
