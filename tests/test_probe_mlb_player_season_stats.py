import unittest
from probe_mlb_player_season_stats import probe

def fixture(url):
    group="hitting" if "group=hitting" in url else "pitching"
    return {"stats":[{"splits":[{"player":{"id":100,"fullName":"Sample Player"},
        "team":{"id":144},"stat":{"gamesPlayed":10,"hits":8 if group=="hitting" else None,
        "inningsPitched":"12.0" if group=="pitching" else None}}]}]}
class MLBPlayerProbeTests(unittest.TestCase):
    def test_both_groups_collected(self):
        result=probe(2025,144,fixture)
        self.assertTrue(result["complete"])
        self.assertEqual(result["groups"]["hitting"]["count"],1)
        self.assertEqual(result["groups"]["pitching"]["count"],1)
    def test_empty_stats_not_approved(self):
        r=probe(2025,144,lambda url:{"stats":[]})
        self.assertFalse(r["complete"])
    def test_missing_team_attribution_rejected(self):
        def missing(url):
            r=fixture(url)
            del r["stats"][0]["splits"][0]["team"]
            return r
        with self.assertRaisesRegex(ValueError,"team attribution"):
            probe(2025,144,missing)
    def test_wrong_team_attribution_rejected(self):
        def wrong(url):
            r=fixture(url)
            r["stats"][0]["splits"][0]["team"]["id"]=147
            return r
        with self.assertRaisesRegex(ValueError,"team attribution"):
            probe(2025,144,wrong)
    def test_duplicate_player_rejected(self):
        def duplicated(url):
            r=fixture(url)
            r["stats"][0]["splits"].append(dict(r["stats"][0]["splits"][0]))
            return r
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            probe(2025,144,duplicated)
if __name__=="__main__":unittest.main()
