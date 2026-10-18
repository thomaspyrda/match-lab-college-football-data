import unittest
from audit_mlb_historical_leader_coverage import verify_team

def hitter(pid, at_bats, hits=0, home_runs=0):
    return {"player_id":pid, "stats":{"atBats":at_bats,"hits":hits,"homeRuns":home_runs}}

def payload(rows, team_id=144):
    return {"stats":[{"splits":[{"team":{"id":team_id},
        "player":{"id":r["player_id"]},"stat":r["stats"]} for r in rows]}]}

class HistoricalLeaderCoverageTests(unittest.TestCase):
    def make_archive(self, rows):
        return {"teams":{"144":{"2020":{"hitters":rows}}}}

    def test_legacy_zero_ab_ignored(self):
        rows = [hitter(7,50,15,2), hitter(8,20,4,0), hitter(9,0)]
        archive = self.make_archive(rows)
        result=verify_team(archive,2020,144,fetcher=lambda url:payload(rows))
        self.assertTrue(result["passed"])
        self.assertEqual(result["excluded_zero_ab"],1)

    def test_missing_higher_ab_hitter_fails(self):
        selected=[hitter(7,50,15,2), hitter(8,20,4,0)]
        reference=[hitter(7,50,15,2), hitter(10,40,8,0), hitter(8,20,4,0)]
        result=verify_team(self.make_archive(selected),2020,144,
                           fetcher=lambda url:payload(reference))
        self.assertFalse(result["passed"])
        self.assertEqual(result["expected_player_ids"],[7,10,8])

    def test_mismatched_hit_count_fails(self):
        result=verify_team(self.make_archive([hitter(7,50,15,2)]),2020,144,
                           fetcher=lambda url:payload([hitter(7,50,14,2)]))
        self.assertFalse(result["passed"])
        self.assertTrue(any(x.get("field")=="hits" for x in result["stat_mismatches"]))

if __name__=="__main__":
    unittest.main()
