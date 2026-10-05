from cfb_dashboard.pipeline.v15 import featured_mismatch, index_rankings, matchup_metrics, team_card


def sample(name, off=80, deff=70):
    return {
        "team": name, "record": "4-1", "ap_rank": None,
        "strength_score": 85.0, "national_strength_rank": 10,
        "offensive_strength": 86.0, "offensive_strength_rank": 8,
        "defensive_strength": 84.0, "defensive_strength_rank": 12,
        "schedule_strength_rank": 20, "schedule_strength_score": 80,
        "unit_strength_model": "validated_v15_recursive_dominance",
        "advanced": {"overall_success": off, "defensive_success": deff, "passing_success": off,
                     "defensive_passing_success": deff, "rushing_success": off,
                     "defensive_rushing_success": deff, "explosiveness": off,
                     "defensive_explosiveness": deff, "finishing_drives": off,
                     "defensive_finishing_drives": deff, "passing_ppa": off,
                     "defensive_passing_ppa": deff, "raw": {}}
    }


def test_rejects_non_v15_payload():
    try:
        index_rankings({"model": {"version": "old"}, "teams": []})
        assert False
    except ValueError:
        assert True


def test_team_card_preserves_v15_and_sos():
    card = team_card(sample("Georgia"))
    assert card["team_strength"] == 85.0
    assert card["offensive_strength_rank"] == 8
    assert card["sos_rank"] == 20


def test_featured_mismatch_is_largest_available_gap():
    away, home = team_card(sample("A", 95, 20)), team_card(sample("B", 40, 85))
    rows = matchup_metrics(away, home)
    best = featured_mismatch(rows)
    assert best is not None
    assert best["percentile_gap"] == 75
