from build_cbb_match_lab_box_snapshots import derive,aggregate,snapshots_for_team,measure

def row(made=0,attempted=10):
 stats={"fieldGoals":{"made":20,"attempted":50},"threePointFieldGoals":{"made":made,"attempted":attempted},
 "freeThrows":{"made":0,"attempted":0},"rebounds":{"offensive":0,"defensive":25,"total":25},"assists":0,"turnovers":{"total":0},"points":{"total":60},"possessions":60}
 return {"teamStats":stats,"opponentStats":stats,"pace":60}

def prior(r,date="2023-11-01T00:00Z"):
 return {"date":date,"stats":derive(r)}

def test_zero_is_observed_not_missing():
 p=aggregate([prior(row())])
 assert p["three_pct"]==0 and p["assists_pg"]==0 and p["oreb_pg"]==0
 assert p["efg_pct"]==40 and p["box_stat_games"]==1
 assert "ft_pct" not in p

def test_weighted_shooting_and_two_game_coverage():
 p=aggregate([prior(row(1,2)),prior(row(1,10),"2023-11-02T00:00Z")])
 assert p["three_pct"]==16.6667
 assert p["box_stat_games"]==2 and p["off_eff"]==100

def test_missing_not_zero_and_no_rebound_total_fallback():
 r=row();del r["teamStats"]["rebounds"]["offensive"]
 assert measure(r,"teamStats","rebounds","offensive") is None
 p=aggregate([prior(r),prior(row())])
 assert "oreb_pg" not in p and p["dreb_pg"]==25
 p=aggregate([prior(row()),{"date":"2023-11-02","stats":{}}])
 assert not p

def test_prior_only_same_day_future_and_missing_boxes():
 expected={"first":{"date":"2023-11-01T00:00Z"},"target":{"date":"2023-11-03T00:00Z"},"same":{"date":"2023-11-03T23:00Z"},"future":{"date":"2023-11-04T00:00Z"}}
 observed={gid:prior(row(1,10),g["date"]) for gid,g in expected.items()}
 snapshots=snapshots_for_team(expected,observed)
 assert "first" not in snapshots
 assert snapshots["target"]["box_stat_games"]==1
 assert snapshots["same"]["box_stat_games"]==1
 assert snapshots["target"]["box_stats_as_of"]==expected["first"]["date"]
 del observed["first"]
 assert "target" not in snapshots_for_team(expected,observed)
