CREATE TABLE IF NOT EXISTS model_scores (
    imdb_id_int integer NOT NULL,
    window_idx integer NOT NULL,
    from_segment_idx integer,
    to_segment_idx integer,
    total_windows integer NOT NULL,
    model text NOT NULL,
    dimension text NOT NULL,
    score real NOT NULL,
    PRIMARY KEY (imdb_id_int, window_idx, model, dimension)
);

CREATE INDEX IF NOT EXISTS idx_model_scores_lookup ON model_scores (imdb_id_int, model, dimension);

