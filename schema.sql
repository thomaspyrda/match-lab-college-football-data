CREATE TABLE match_lab_ap_elo (
  season SMALLINT NOT NULL,
  effective_week SMALLINT NOT NULL,
  team VARCHAR(100) NOT NULL,
  is_ap_ranked BOOLEAN NOT NULL,
  ap_rank SMALLINT NULL,
  ap_points INT NULL,
  ap_first_place_votes INT NULL,
  elo_rating INT NULL,
  elo_rank SMALLINT NULL,
  fbs_field_size SMALLINT NULL,
  ap_source_week SMALLINT NOT NULL,
  elo_snapshot_week SMALLINT NOT NULL,
  timing_status VARCHAR(24) NOT NULL,
  PRIMARY KEY (season, effective_week, team),
  CHECK ((is_ap_ranked = TRUE AND ap_rank BETWEEN 1 AND 25) OR
         (is_ap_ranked = FALSE AND ap_rank IS NULL)),
  CHECK (elo_rank IS NULL OR elo_rank BETWEEN 1 AND fbs_field_size)
);

CREATE INDEX idx_match_lab_ap_elo_lookup
  ON match_lab_ap_elo (season, effective_week, team);

CREATE TABLE match_lab_game_ap_elo (
  game_id BIGINT NOT NULL,
  season SMALLINT NOT NULL,
  week SMALLINT NOT NULL,
  start_date DATETIME NULL,
  team VARCHAR(100) NOT NULL,
  side VARCHAR(4) NOT NULL,
  opponent VARCHAR(100) NOT NULL,
  is_ap_ranked BOOLEAN NOT NULL,
  ap_rank SMALLINT NULL,
  pregame_elo INT NULL,
  pregame_elo_rank SMALLINT NULL,
  elo_source VARCHAR(24) NOT NULL,
  fbs_field_size SMALLINT NOT NULL,
  timing_status VARCHAR(24) NOT NULL,
  PRIMARY KEY (game_id, team)
);
