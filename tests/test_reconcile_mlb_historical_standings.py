import unittest
from reconcile_mlb_historical_standings import reconcile

def fixtures():
    mapping={"teams":{str(i):{"slug":f"team-{i}"} for i in range(1,31)}}
    games={"10":{"phase":"regular","home":{"slug":"team-1","runs":5},"away":{"slug":"team-2","runs":2}}}
    stage={"season":2020,"games":games}
    standings={"records":[{"teamRecords":[{"team":{"id":i},"wins":1 if i==1 else 0,"losses":1 if i==2 else 0} for i in range(1,31)]}]}
    return stage,mapping,standings

class ReconciliationTests(unittest.TestCase):
    def test_all_team_records_match(self):
        a,b,c=fixtures()
        r=reconcile(a,b,c)
        self.assertEqual(r["teams_matching"],30)
    def test_score_mismatch_detected(self):
        a,b,c=fixtures()
        a["games"]["10"]["home"]["runs"]=1
        r=reconcile(a,b,c)
        self.assertEqual(r["teams_matching"],28)
    def test_incomplete_standings_fail_closed(self):
        a,b,c=fixtures()
        c["records"][0]["teamRecords"].pop()
        with self.assertRaisesRegex(ValueError,"Standings incomplete"):
            reconcile(a,b,c)
if __name__=="__main__": unittest.main()
