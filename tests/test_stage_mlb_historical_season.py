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
    def test_scoreless_final_is_quarantined(self):
        def scoreless(url):
            r=fixture(url)
            del r["dates"][0]["games"][0]["teams"]["home"]["score"]
            return r
        result=stage_season(2020,crosswalk(),scoreless)
        self.assertEqual(result["coverage"]["quarantined_scoreless_games"],1)
        self.assertEqual(result["coverage"]["regular_games"],0)
        self.assertEqual(result["warnings"][0]["game_id"],"10")
    def test_duplicate_rejected(self):
        def repeated(url):
            r=fixture(url)
            r["dates"][0]["games"].append(dict(r["dates"][0]["games"][0]))
            return r
        result=stage_season(2020,crosswalk(),repeated)
        self.assertEqual(result["coverage"]["identical_duplicates_ignored"],1)
        self.assertEqual(result["coverage"]["regular_games"],1)
    def test_conflicting_duplicate_rejected(self):
        def conflicting(url):
            r=fixture(url)
            duplicate=__import__("copy").deepcopy(r["dates"][0]["games"][0])
            duplicate["teams"]["home"]["score"]=8
            r["dates"][0]["games"].append(duplicate)
            return r
        with self.assertRaisesRegex(ValueError,"Conflicting duplicate"):
            stage_season(2020,crosswalk(),conflicting)
    def test_2021_exception_targets(self):
        def empty(url): return {"dates":[]}
        result=stage_season(2021,crosswalk(),empty)
        self.assertEqual(result["coverage"]["regular_games"],0)
        self.assertEqual(result["coverage"]["teams_below_expected"],30)
    def test_2026_canceled_finale_expected_team_totals(self):
        mapping=crosswalk()
        mapping["teams"]["1"]["slug"]="baltimore-orioles"
        mapping["teams"]["2"]["slug"]="new-york-yankees"
        result=stage_season(2026,mapping,lambda url: {"dates":[]})
        self.assertEqual(result["coverage"]["teams_below_expected"],30)
        # Explicitly verify these two teams are expected to play 161, not 162.
        self.assertEqual(result["coverage"]["expected_team_game_counts"]["baltimore-orioles"],161)
        self.assertEqual(result["coverage"]["expected_team_game_counts"]["new-york-yankees"],161)
        self.assertEqual(result["coverage"]["expected_team_game_counts"]["team-3"],162)
    def test_invalid_score_rejected(self):
        def invalid(url):
            r=fixture(url)
            r["dates"][0]["games"][0]["teams"]["home"]["score"]=-1
            return r
        with self.assertRaisesRegex(ValueError,"Invalid"):
            stage_season(2020,crosswalk(),invalid)
if __name__=="__main__":
    unittest.main()
