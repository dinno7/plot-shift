CREATE TABLE IF NOT EXISTS movies_meta(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  imdb_id TEXT NOT NULL,
  imdb_id_int INTEGER GENERATED ALWAYS AS (CAST(SUBSTR(imdb_id, 3) AS INTEGER)),
  average_rating REAL NOT NULL,
  num_votes INTEGER NOT NULL,
  title_type TEXT NOT NULL,
  primary_title TEXT NOT NULL,
  original_title TEXT NOT NULL,
  start_year INTEGER NOT NULL,
  runtime_minutes INTEGER NOT NULL,
  genres TEXT
);
