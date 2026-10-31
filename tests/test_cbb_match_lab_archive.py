import datetime
from build_cbb_match_lab_archive import validated

def game():
    return {"game_id":"test-1","season":2025,"date":"2025-01-10T19:00:00+00:00",
      "snapshot_as_of":"2025-01-10T17:00:00+00:00","result_verified_at":"2025-01-11T01:00:00+00:00",
      "pregame_verified":True,"historical_snapshot_source":"timestamped pregame archive",
      "pregame_source":"historical snapshot","result_source":"official final",
      "market_source":"archived bookmaker line",
      "away":{"name":"A"},"home":{"name":"B"},
      "market":{"spread":-3.5,"total":145.5},
      "result":{"verified":True,"away_points":75,"home_points":72,"total":"over"}}

def test_valid_game():assert validated(game())
def test_reject_future_snapshot():
    g=game();g["snapshot_as_of"]="2025-01-10T20:00:00+00:00";assert not validated(g)
def test_reject_unverified_final():
    g=game();g["result"]["verified"]=False;assert not validated(g)
def test_reject_bad_total():
    g=game();g["result"]["total"]="under";assert not validated(g)
def test_reject_missing_market():
    g=game();g["market"].pop("spread");assert not validated(g)
def test_reject_unverified_pregame():
    g=game();g["pregame_verified"]=False;assert not validated(g)
