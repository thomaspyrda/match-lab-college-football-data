import unittest
from datetime import datetime, timezone
from sync_cbb_market_archives import capture_event

class MarketSafetyTests(unittest.TestCase):
    def event(self):
        return {
            "id": "123", "date": "2026-11-01T19:00:00Z",
            "season": {"year": 2027}, "status": {"type": {"completed": False}},
            "competitions": [{"competitors": [
                {"homeAway": "home", "team": {"id": "87"}},
                {"homeAway": "away", "team": {"id": "222"}}
            ], "odds": [{"spread": 4.5, "overUnder": 142.5,
                         "homeTeamOdds": {"favorite": True},
                         "awayTeamOdds": {"favorite": False},
                         "provider": {"name": "Recorded Provider"}}]}]
        }

    def test_pretip_quote_is_accepted(self):
        row = capture_event(self.event(), datetime(2026,11,1,18,0,tzinfo=timezone.utc))
        self.assertEqual(row["home_spread"], -4.5)
        self.assertEqual(row["total"], 142.5)

    def test_posttip_quote_rejected(self):
        self.assertIsNone(capture_event(self.event(),datetime(2026,11,1,19,1,tzinfo=timezone.utc)))

    def test_completed_event_rejected(self):
        event = self.event()
        event["status"]["type"]["completed"] = True
        self.assertIsNone(capture_event(event,datetime(2026,11,1,18,0,tzinfo=timezone.utc)))

    def test_unverified_spread_side_not_assumed(self):
        event = self.event()
        del event["competitions"][0]["odds"][0]["homeTeamOdds"]
        del event["competitions"][0]["odds"][0]["awayTeamOdds"]
        row = capture_event(event,datetime(2026,11,1,18,0,tzinfo=timezone.utc))
        self.assertIsNone(row["home_spread"])
        self.assertEqual(row["total"],142.5)

if __name__ == "__main__":
    unittest.main()

class OfflineGradingTests(unittest.TestCase):
    def test_all_final_games_grade_without_provider_requests(self):
        import json, tempfile
        from pathlib import Path
        from unittest.mock import patch
        import sync_cbb_market_archives as m
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); teams=root/'teams'; teams.mkdir()
            ledger=root/'ledger.json'; markets=root/'markets'; entries={}
            for gid,home,away,hp,ap,spread,total in [('a','333','2534',96,74,-27.5,172.5),('b','8','2029',106,61,-41.5,166.5)]:
                entries[gid]={'id':gid,'home':home,'away':away,'tipoff':'2026-11-04T00:30:00Z','observed_at':'2026-11-03T23:27:00Z','home_spread':spread,'total':total,'source':'fixture','provider':'Verified pregame','line_type':'pregame'}
                for tid,own,opp in [(home,hp,ap),(away,ap,hp)]:
                    (teams/(tid+'.json')).write_text(json.dumps({'team_id':tid,'seasons':{'2027':{'phases':{'regular':{'games':[{'id':gid,'status':'final','points':own,'opponent_points':opp}]},'postseason':{'games':[]}}}}}))
            ledger.write_text(json.dumps({'season':2027,'last_checked':'unchanged','games':entries}))
            with patch.object(m,'LEDGER',ledger),patch.object(m,'TEAMS',teams),patch.object(m,'MARKETS',markets),patch.object(m.urllib.request,'urlopen',side_effect=AssertionError('Offline grading must not fetch')):
                m.update(capture=False)
            for tid,ats,ou in [('333','L','U'),('2534','W','U'),('8','W','O'),('2029','L','O')]:
                row=next(iter(json.loads((markets/(tid+'.json')).read_text())['games']['2027'].values()))
                self.assertEqual((row['ats'],row['ou']),(ats,ou))
            self.assertEqual(json.loads(ledger.read_text())['last_checked'],'unchanged')
