CREATE TABLE IF NOT EXISTS reversal_features (
    imdb_id_int integer NOT NULL,
    model text NOT NULL,
    dimension text NOT NULL,
    prominence real NOT NULL,
    series_length integer NOT NULL,
    n_reversals integer NOT NULL,
    n_windows integer,
    mean_intensity real NOT NULL,
    max_intensity real NOT NULL,
    PRIMARY KEY (imdb_id_int, model, dimension),
    FOREIGN KEY (imdb_id_int) REFERENCES movies_meta (imdb_id_int) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reversal_features_lookup ON reversal_features (model, dimension, imdb_id_int);

