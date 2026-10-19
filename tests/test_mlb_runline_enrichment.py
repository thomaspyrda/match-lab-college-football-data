#!/usr/bin/env python3
"""Deterministic synthetic unit tests; NOT a historical data validation report."""
import importlib.util
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("enrich",ROOT/"scripts/enrich_mlb_runlines.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def official():
    return {"teams":{
        "new-york-yankees":{"games":[{"date":"2024-04-01","opponent":"boston-red-sox","location":"Home","result":"W","score":"5-3"}],"record":{"wins":1,"losses":0}},
        "boston-red-sox":{"games":[{"date":"2024-04-01","opponent":"new-york-yankees","location":"Away","result":"L","score":"3-5"}],"record":{"wins":0,"losses":1}}
    }}
def odds(hspread=-1.5):
    return {"2024-04-01":[{"gameView":{"gameType":"R","homeTeam":{"shortName":"NYY"},"awayTeam":{"shortName":"BOS"},"homeTeamScore":5,"awayTeamScore":3},"odds":{"pointspread":[{"sportsbook":"fanduel","currentLine":{"homeSpread":hspread,"awaySpread":-hspread}}]}}]}

class RunlineTests(unittest.TestCase):
    def test_slug_mapping(self):
        self.assertEqual(m.code("new-york-yankees"),"NYY")
        self.assertEqual(m.code("boston-red-sox"),"BOS")
    def test_team_result_and_opponent_inversion(self):
        data=official();r=m.enrich(data,odds(),2024)
        self.assertEqual(r["enriched_games"],1)
        y=data["teams"]["new-york-yankees"]["games"][0]
        b=data["teams"]["boston-red-sox"]["games"][0]
        self.assertEqual((y["team_runline_side"],y["team_runline_result"]),(-1.5,"W"))
        self.assertEqual((b["team_runline_side"],b["team_runline_result"]),(1.5,"L"))
    def test_conflicting_odds_rejected(self):
        data=official(); archive=odds()
        clone=odds(1.5)["2024-04-01"][0]
        archive["2024-04-01"].append(clone)
        r=m.enrich(data,archive,2024)
        self.assertEqual(r["enriched_games"],0)
        self.assertNotIn("team_runline_side",data["teams"]["new-york-yankees"]["games"][0])
    def test_unverified_removes_stale_fields(self):
        data=official()
        data["teams"]["new-york-yankees"]["games"][0]["team_runline_side"]=1.5
        m.enrich(data,{},2024)
        self.assertNotIn("team_runline_side",data["teams"]["new-york-yankees"]["games"][0])

if __name__=="__main__":unittest.main()
