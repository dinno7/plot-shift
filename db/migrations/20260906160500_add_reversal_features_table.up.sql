CREATE TABLE IF NOT EXISTS reversal_features (
    imdb_id_int integer NOT NULL,
    scorer_name text NOT NULL,
    dimension text NOT NULL,
    trend_window_size real NOT NULL,
    series_length integer NOT NULL,
    n_reversals integer NOT NULL,
    n_windows integer NOT NULL DEFAULT 0,
    window_duration real NOT NULL DEFAULT 0.0,
    mean_intensity real NOT NULL,
    max_intensity real NOT NULL,
    detector_name text NOT NULL,
    PRIMARY KEY (imdb_id_int, scorer_name, detector_name, dimension)
);

CREATE INDEX IF NOT EXISTS idx_reversal_features_lookup ON reversal_features (scorer_name, dimension, imdb_id_int);

