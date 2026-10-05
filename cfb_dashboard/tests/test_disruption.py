from cfb_dashboard.pipeline.disruption import accumulate_boxes, season_metrics

def team(name, sacks, passes, turnovers):
    return {"team": name, "stats": [{"category": "sacks", "stat": str(sacks)}, {"category": "completionAttempts", "stat": f"10-{passes}"}, {"category": "turnovers", "stat": str(turnovers)}]}

def test_sacks_use_opponent_sacks_and_attempts_with_mirrored_turnovers():
    totals = {}
    accumulate_boxes([{"teams": [team("A", 3, 27, 2), team("B", 1, 37, 0)]}], totals)
    a, b = season_metrics(totals["A"]), season_metrics(totals["B"])
    assert a["sack_rate"] == 3/40
    assert a["sack_rate_allowed"] == 1/28
    assert b["sack_rate"] == a["sack_rate_allowed"]
    assert a["turnovers"] == b["turnovers_forced"] == 2
    assert a["turnovers_forced"] == b["turnovers"] == 0

def test_missing_box_categories_are_not_reported_as_zero():
    totals = {}
    accumulate_boxes([{"teams": [{"team": "A", "stats": []}, team("B", 1, 20, 2)]}], totals)
    assert all(value is None for value in season_metrics(totals["A"]).values())

def test_rates_weight_dropbacks_instead_of_averaging_game_rates():
    totals = {}
    accumulate_boxes([{"teams": [team("A", 1, 20, 0), team("B", 0, 9, 1)]}, {"teams": [team("A", 2, 30, 1), team("B", 0, 38, 0)]}], totals)
    assert season_metrics(totals["A"])["sack_rate"] == 3/50
    assert season_metrics(totals["A"])["turnovers_forced"] == 1
