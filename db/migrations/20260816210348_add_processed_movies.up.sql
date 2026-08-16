CREATE TABLE IF NOT EXISTS processed_movies (
  imdb_id_int INTEGER PRIMARY KEY,
  total_words INTEGER,
  duration_minutes REAL,
  is_valid BOOLEAN,
  clean_text TEXT
);
