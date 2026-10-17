import unittest
from stage_mlb_daily_backfill import build

class MLBStageTest(unittest.TestCase):
    def test_final_and_incomplete(self):
        schedule={"dates":[{"games":[
          {"gamePk":1,"gameType":"L","officialDate":"2026-10-16","status":{"abstractGameState":"Final"},"teams":{"home":{"team":{"id":1},"score":5},"away":{"team":{"id":2},"score":3}}},
          {"gamePk":2,"status":{"abstractGameState":"Final"},"teams":{"home":{"team":{"id":1}},"away":{"team":{"id":2}}}}
        ]}]}
        box={"teams":{"home":{"players":{"ID1":{"person":{"id":12,"fullName":"Test Batter"},"stats":{"batting":{"hits":2}}}}},"away":{"players":{"ID2":{"person":{"id":13,"fullName":"Test Pitcher"},"stats":{"pitching":{"inningsPitched":"5.0"}}}}}}}
        def fetch(path):return schedule if path.startswith("/schedule") else box
        r=build("2026-10-16","2026-10-17",fetch)
        self.assertEqual(r["coverage"]["validated_games"],1)
        self.assertEqual(r["coverage"]["player_records"],2)
        self.assertEqual(r["coverage"]["warnings"],1)
        self.assertIsNone(r["games"]["1"]["market"])
        self.assertEqual(r["games"]["1"]["players"]["home"][0]["batting"]["hits"],2)

if __name__=="__main__":unittest.main()
