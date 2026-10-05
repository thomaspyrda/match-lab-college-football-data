from cfb_dashboard.pipeline.build_dashboard import metric_rows, mismatch, team_payload, build_trends


def test_team_payload_prefers_frozen_v15_values():
    profile={"strength_score":70,"national_strength_rank":40,"ap_rank":12,"recent_form":{"wins":4,"losses":1},"advanced":{}}
    ranking={"strength_score":91.4,"national_strength_rank":3,"offensive_strength":92.0,"offensive_strength_rank":2,
             "defensive_strength":89.0,"defensive_strength_rank":7,"schedule_strength_rank":18,"team_strength_sd":1.9,"record":"5-0"}
    row=team_payload("Example",profile,ranking)
    assert row["team_strength"] == 91.4
    assert row["team_strength_rank"] == 3
    assert row["record"] == "5-0"


def test_metric_rows_compare_corresponding_units():
    away={"advanced":{"overall_success":90,"defensive_success":40}}
    home={"advanced":{"overall_success":60,"defensive_success":20}}
    rows=metric_rows(away,home)
    success=next(r for r in rows if r["label"]=="Overall Success Rate")
    assert success["away_offense"] == 90
    assert success["home_defense"] == 20
    assert success["home_offense"] == 60
    assert success["away_defense"] == 40


def test_featured_mismatch_selects_largest_gap():
    best=mismatch([
        {"label":"A","away_offense":90,"home_defense":10,"home_offense":60,"away_defense":50},
        {"label":"B","away_offense":80,"home_defense":40,"home_offense":70,"away_defense":60},
    ])
    assert best["metric"] == "A"
    assert best["side"] == "away_offense"
    assert best["percentile_gap"] == 80

def test_team_payload_preserves_recent_form():
    profile={"recent_form":{"games":5,"wins":4,"losses":1,"avg_points":31.2,"avg_allowed":18.4,"coming_off_loss":False},"advanced":{}}
    row=team_payload("Example",profile,{"record":"4-1"})
    assert row["form"]["avg_points"] == 31.2
    assert row["form"]["avg_allowed"] == 18.4
    assert row["form"]["coming_off_loss"] is False

def test_v15_situational_metrics_override_empty_profile_slots():
    ranking={"dashboard_situational":{"third_down_conversion":1.25,"defensive_third_down_conversion":0.75,"red_zone_td_rate":1.1}}
    row=team_payload("Example",{"advanced":{"overall_success":80}},ranking)
    assert row["metrics"]["third_down_conversion"] == 1.25
    assert row["metrics"]["defensive_third_down_conversion"] == 0.75
    assert row["metrics"]["red_zone_td_rate"] == 1.1
    assert row["metrics"]["overall_success"] == 80

def test_build_trends_prioritizes_large_matchup_edges():
    away={"name":"Away","team_strength_rank":10}
    home={"name":"Home","team_strength_rank":40}
    rows=[
      {"label":"Third Down Conversion","away_offense":90,"home_defense":50,"home_offense":55,"away_defense":52},
      {"label":"Explosiveness","away_offense":60,"home_defense":55,"home_offense":80,"away_defense":50},
    ]
    trends=build_trends(away,home,rows)
    assert trends[0]["metric"] == "Third Down Conversion"
    assert trends[0]["gap"] == 40
    assert any(x["type"]=="strength_gap" and x["team"]=="Away" for x in trends)