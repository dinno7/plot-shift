CREATE TABLE IF NOT EXISTS reversal_features(
  imdb_id_int INTEGER NOT NULL,
  model TEXT NOT NULL,
  dimension TEXT NOT NULL,
  prominence REAL NOT NULL,
  series_length INTEGER NOT NULL,
  n_reversals INTEGER NOT NULL,
  mean_intensity REAL NOT NULL,
  max_intensity REAL NOT NULL,
  PRIMARY KEY (imdb_id_int, model, dimension),
  FOREIGN KEY (imdb_id_int) REFERENCES movies_meta(imdb_id_int) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_reversal_features_lookup
ON reversal_features(model, dimension, imdb_id_int);
