import unittest
from build_mlb_game_results import build, IDS

class TestMlbGameResults(unittest.TestCase):
    def game(self, gid, state, hs=None, ac=None, date="2025-06-01"):
        return {
            "gamePk":gid,"gameType":"R","officialDate":date,
            "status":{"abstractGameState":state},
            "teams":{"home":{"team":{"id":147},**({"score":hs} if hs is not None else {})},
                     "away":{"team":{"id":111},**({"score":ac} if ac is not None else {})}}
        }
    def test_postponed_cancelled_scoreless_and_doubleheader(self):
        games=[
            self.game(100,"Preview"),
            self.game(101,"Final"), # Marked final but with no reported result
            self.game(102,"Final",5,3),
            self.game(103,"Final",3,8),
            self.game(104,"Postponed"),
            self.game(102,"Final",5,3), # duplicate API entry
        ]
        data=build(2025,{"dates":[{"games":games}]})
        ny=data["teams"][IDS[147]]
        bos=data["teams"][IDS[111]]
        self.assertEqual(len(ny["games"]),2)
        self.assertEqual(len(bos["games"]),2)
        self.assertEqual(ny["record"]["wins"],1)
        self.assertEqual(ny["record"]["losses"],1)
        self.assertEqual(ny["record"]["runline_wins"],1)
        self.assertEqual(ny["record"]["overs"],1)
        self.assertEqual(len(data["quarantined"]),1)
        self.assertEqual(data["quarantined"][0]["game_id"],101)
        self.assertEqual(ny["games"][0]["game_id"],102)
        self.assertEqual(ny["games"][1]["game_id"],103)

if __name__=="__main__":
    unittest.main()
