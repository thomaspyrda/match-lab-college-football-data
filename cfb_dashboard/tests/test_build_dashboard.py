from cfb_dashboard.pipeline.build_dashboard import metric_rows, mismatch, team_payload, build_trends, market_record, market_trends, player_cards


def test_team_payload_prefers_frozen_v15_values():
    profile={"strength_score":70,"national_strength_rank":40,"ap_rank":12,"recent_form":{"wins":4,"losses":1},"advanced":{}}
    ranking={"strength_score":91.4,"national_strength_rank":3,"offensive_strength":92.0,"offensive_strength_rank":2,
             "defensive_strength":89.0,"defensive_strength_rank":7,"schedule_strength_rank":18,"team_strength_sd":1.9,"record":"5-0"}
    row=team_payload("Example",profile,ranking)
    assert row["team_strength"] == 91.4
    assert row["team_strength_rank"] == 3
    assert row["record"] == "5-0"


def test_metric_rows_compare_raw_source_stats_and_fbs_ranks():
    away={"raw_metrics":{"overall_success":0.44,"overall_success_rank":78,"defensive_success":0.36,"defensive_success_rank":22}}
    home={"raw_metrics":{"overall_success":0.51,"overall_success_rank":31,"defensive_success":0.42,"defensive_success_rank":83}}
    rows=metric_rows(away,home)
    success=next(r for r in rows if r["label"]=="Success Rate")
    assert success["away_offense"] == 0.44
    assert success["away_offense_rank"] == 78
    assert success["home_defense"] == 0.42
    assert success["home_defense_rank"] == 83
    assert success["home_offense"] == 0.51
    assert success["away_defense"] == 0.36


def test_featured_mismatch_selects_largest_fbs_rank_gap():
    best=mismatch([
        {"label":"A","away_offense":0.44,"home_defense":0.39,"home_offense":0.51,"away_defense":0.36,
         "away_offense_rank":78,"home_defense_rank":15,"home_offense_rank":31,"away_defense_rank":22},
        {"label":"B","away_offense":0.12,"home_defense":0.08,"home_offense":0.20,"away_defense":0.10,
         "away_offense_rank":40,"home_defense_rank":55,"home_offense_rank":30,"away_defense_rank":45},
    ])
    assert best["metric"] == "A"
    assert best["side"] == "away_offense"
    assert best["rank_gap"] == 63

def test_team_payload_preserves_recent_form():
    profile={"recent_form":{"games":5,"wins":4,"losses":1,"avg_points":31.2,"avg_allowed":18.4,"coming_off_loss":False},"advanced":{}}
    row=team_payload("Example",profile,{"record":"4-1"})
    assert row["form"]["avg_points"] == 31.2
    assert row["form"]["avg_allowed"] == 18.4
    assert row["form"]["coming_off_loss"] is False

def test_dashboard_cards_do_not_require_v15_situational_values():
    row=team_payload("Example",{"advanced":{"overall_success":80}},{"dashboard_situational":{"third_down_conversion":1.25}})
    assert row["metrics"]["third_down_conversion"] == 1.25
    # metric_rows ignores model diagnostics and reads raw_metrics only.
    rows=metric_rows({"raw_metrics":{"third_down_conversion":0.42,"third_down_conversion_rank":57}},
                     {"raw_metrics":{"defensive_third_down_conversion":0.36,"defensive_third_down_conversion_rank":24}})
    third=next(r for r in rows if r["label"]=="Third Down Conversion")
    assert third["away_offense"] == 0.42
    assert third["away_offense_rank"] == 57
    assert third["home_defense"] == 0.36
    assert third["home_defense_rank"] == 24

def test_build_trends_prioritizes_large_fbs_rank_edges():
    away={"name":"Away","team_strength_rank":10}
    home={"name":"Home","team_strength_rank":40}
    rows=[
      {"label":"Third Down Conversion","away_offense":0.50,"home_defense":0.35,"home_offense":0.40,"away_defense":0.38,
       "away_offense_rank":8,"home_defense_rank":72,"home_offense_rank":60,"away_defense_rank":55},
      {"label":"Explosiveness","away_offense":1.30,"home_defense":1.20,"home_offense":1.25,"away_defense":1.15,
       "away_offense_rank":30,"home_defense_rank":40,"home_offense_rank":45,"away_defense_rank":50},
    ]
    trends=build_trends(away,home,rows)
    assert trends[0]["metric"] == "Third Down Conversion"
    assert trends[0]["gap"] == 64
    assert any(x["type"]=="strength_gap" and x["team"]=="Away" for x in trends)

def test_team_payload_prefers_current_ap_rank_and_keeps_form():
    profile={"ap_rank":18,"recent_form":{"games":4,"wins":3,"losses":1},"advanced":{}}
    ranking={"ap_rank":11,"record":"4-0"}
    row=team_payload("Example",profile,ranking)
    assert row["ap_rank"] == 11
    assert row["form"]["games"] == 4


def test_game_context_trends_are_bounded_and_explicit():
    away={"name":"Away","team_strength_rank":20,"ap_rank":8,"form":{"coming_off_loss":True}}
    home={"name":"Home","team_strength_rank":50,"ap_rank":None,"form":{"coming_off_loss":False}}
    trends=build_trends(away,home,[],{"conference_game":True,"neutral_site":True})
    types=[x["type"] for x in trends]
    assert "ranked_context" in types
    assert "bounce_back" in types
    assert sum(x["type"]=="game_context" for x in trends) == 2
    assert len(trends) <= 8


def test_metric_grid_has_eight_raw_stat_pairs():
    rows=metric_rows({"raw_metrics":{}},{"raw_metrics":{}})
    assert len(rows) == 8
    assert rows[0]["offense_label"] == "Success Rate"
    assert rows[0]["defense_label"] == "Defensive Success Rate"
    assert rows[0]["format"] == "percent"
    assert rows[-1]["offense_label"] == "Red Zone Efficiency"


def test_market_record_ats_and_ou():
    games=[
      {"home":"A","away":"B","neutral_site":False,"result":{"ats":"home_cover","total":"over"}},
      {"home":"C","away":"A","neutral_site":False,"result":{"ats":"away_cover","total":"under"}},
      {"home":"A","away":"D","neutral_site":False,"result":{"ats":"push","total":"push"}},
    ]
    assert market_record("A",games,"ats") == "2-0-1"
    assert market_record("A",games,"ou") == "1-1-1"
    assert market_record("A",games,"ats","home") == "1-0-1"
    assert market_record("A",games,"ats","away") == "1-0-0"


def test_location_market_record_excludes_neutral_site():
    games=[
      {"home":"A","away":"B","neutral_site":True,"result":{"ats":"home_cover","total":"over"}},
      {"home":"A","away":"C","neutral_site":False,"result":{"ats":"away_cover","total":"under"}},
    ]
    assert market_record("A",games,"ats","home") == "0-1-0"
    assert market_record("A",games,"ou","home") == "0-1-0"


def test_market_trends_builds_four_nfl_style_rows():
    games=[{"home":"Home","away":"Away","neutral_site":False,"result":{"ats":"home_cover","total":"over"}}]
    rows=market_trends({"name":"Away"},{"name":"Home"},games)
    assert [r["label"] for r in rows] == ["ATS this season","ATS by location","O/U this season","O/U by location"]
    assert rows[0]["away"] == "0-1-0"
    assert rows[0]["home"] == "1-0-0"


def test_player_cards_always_returns_top_four_or_placeholders():
    team={"name":"Example","abbr":"EX"}
    usage={"Example":[
      {"name":"P1","position":"RB","overall":0.45},
      {"name":"P2","position":"WR","overall":0.35},
    ]}
    cards=player_cards(team,usage)
    assert len(cards) == 4
    assert cards[0]["name"] == "P1"
    assert cards[1]["name"] == "P2"
    assert cards[2]["placeholder"] is True
    assert cards[3]["placeholder"] is True


def test_raw_metric_rows_use_explicit_source_ranks_without_recalculation():
    away={"raw_metrics":{"offensive_ppa":0.25,"offensive_ppa_rank":17,"defensive_ppa":0.12,"defensive_ppa_rank":31}}
    home={"raw_metrics":{"offensive_ppa":0.18,"offensive_ppa_rank":38,"defensive_ppa":0.09,"defensive_ppa_rank":22}}
    row=next(r for r in metric_rows(away,home) if r["label"]=="EPA / Play")
    assert row["away_offense"] == 0.25
    assert row["away_offense_rank"] == 17
    assert row["home_defense"] == 0.09
    assert row["home_defense_rank"] == 22
