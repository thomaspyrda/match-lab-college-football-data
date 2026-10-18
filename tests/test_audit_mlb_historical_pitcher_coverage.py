import unittest
from audit_mlb_historical_pitcher_coverage import verify_pitchers

def row(pid, gp, gs):
    return {"player_id":pid,"stats":{"gamesPlayed":gp,"gamesStarted":gs}}

def response(rows):
    return {"stats":[{"splits":[{"team":{"id":144},"player":{"id":r["player_id"]},"stat":r["stats"]} for r in rows]}]}

class PitcherAuditTests(unittest.TestCase):
    def test_correct_starters_and_relievers(self):
        rows=[row(i,25,20) for i in range(1,6)]+[row(i,60,0) for i in range(6,11)]
        archive={"teams":{"144":{"2025":{"starters":rows[:5],"relievers":rows[5:]}}}}
        result=verify_pitchers(archive,2025,144,fetcher=lambda url:response(rows))
        self.assertTrue(result["passed"])

    def test_missing_higher_start_pitcher_fails(self):
        rows=[row(i,25,20) for i in range(1,6)]+[row(11,30,25)]+[row(i,60,0) for i in range(6,11)]
        archive={"teams":{"144":{"2025":{"starters":rows[:5],"relievers":rows[6:]}}}}
        result=verify_pitchers(archive,2025,144,fetcher=lambda url:response(rows))
        self.assertFalse(result["passed"])
        self.assertEqual(result["groups"]["starters"]["expected_ids"][0],11)

    def test_missing_higher_relief_pitcher_fails(self):
        rows=[row(i,25,20) for i in range(1,6)]+[row(i,60,0) for i in range(6,11)]+[row(12,80,0)]
        archive={"teams":{"144":{"2025":{"starters":rows[:5],"relievers":rows[5:10]}}}}
        result=verify_pitchers(archive,2025,144,fetcher=lambda url:response(rows))
        self.assertFalse(result["passed"])
        self.assertEqual(result["groups"]["relievers"]["expected_ids"][0],12)

if __name__=="__main__":
    unittest.main()
