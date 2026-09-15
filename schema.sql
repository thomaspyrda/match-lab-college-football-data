CREATE TABLE match_lab_ap_elo (
 season SMALLINT NOT NULL,effective_week SMALLINT NOT NULL,team VARCHAR(100) NOT NULL,is_ap_ranked BOOLEAN NOT NULL,ap_rank SMALLINT NULL,ap_points INT NULL,ap_first_place_votes INT NULL,elo_rating INT NULL,elo_rank SMALLINT NULL,strength_score SMALLINT NULL,strength_tier VARCHAR(16) NULL,top_percent SMALLINT NULL,fbs_field_size SMALLINT NULL,ap_source_week SMALLINT NOT NULL,elo_snapshot_week SMALLINT NOT NULL,timing_status VARCHAR(24) NOT NULL,
 PRIMARY KEY(season,effective_week,team),CHECK(strength_score IS NULL OR strength_score BETWEEN 1 AND 100),CHECK(top_percent IS NULL OR top_percent BETWEEN 1 AND 100)
);
CREATE INDEX idx_match_lab_ap_elo_lookup ON match_lab_ap_elo(season,effective_week,team);
CREATE TABLE match_lab_game_ap_elo (
 game_id BIGINT NOT NULL,season SMALLINT NOT NULL,week SMALLINT NOT NULL,start_date DATETIME NULL,team VARCHAR(100) NOT NULL,side VARCHAR(4) NOT NULL,opponent VARCHAR(100) NOT NULL,is_ap_ranked BOOLEAN NOT NULL,ap_rank SMALLINT NULL,pregame_elo INT NULL,pregame_elo_rank SMALLINT NULL,strength_score SMALLINT NULL,strength_tier VARCHAR(16) NULL,top_percent SMALLINT NULL,elo_source VARCHAR(24) NOT NULL,fbs_field_size SMALLINT NOT NULL,timing_status VARCHAR(24) NOT NULL,
 PRIMARY KEY(game_id,team),CHECK(strength_score IS NULL OR strength_score BETWEEN 1 AND 100),CHECK(top_percent IS NULL OR top_percent BETWEEN 1 AND 100)
);
CREATE TABLE match_lab_advanced_profile (
 season SMALLINT NOT NULL,effective_week SMALLINT NOT NULL,through_week SMALLINT NOT NULL,team VARCHAR(100) NOT NULL,games_played SMALLINT NOT NULL,offensive_efficiency SMALLINT NULL,defensive_efficiency SMALLINT NULL,rushing_success SMALLINT NULL,passing_success SMALLINT NULL,explosiveness SMALLINT NULL,havoc SMALLINT NULL,finishing_drives SMALLINT NULL,metrics_available SMALLINT NOT NULL,
 PRIMARY KEY(season,effective_week,team),CHECK(through_week=effective_week-1),CHECK(metrics_available BETWEEN 0 AND 7),CHECK(offensive_efficiency IS NULL OR offensive_efficiency BETWEEN 1 AND 100),CHECK(defensive_efficiency IS NULL OR defensive_efficiency BETWEEN 1 AND 100),CHECK(rushing_success IS NULL OR rushing_success BETWEEN 1 AND 100),CHECK(passing_success IS NULL OR passing_success BETWEEN 1 AND 100),CHECK(explosiveness IS NULL OR explosiveness BETWEEN 1 AND 100),CHECK(havoc IS NULL OR havoc BETWEEN 1 AND 100),CHECK(finishing_drives IS NULL OR finishing_drives BETWEEN 1 AND 100)
);
CREATE INDEX idx_match_lab_advanced_lookup ON match_lab_advanced_profile(season,effective_week,team);
