CREATE TABLE IF NOT EXISTS subtitles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  idx INTEGER NOT NULL,
  imdb_id_int INTEGER NOT NULL,
  start_seconds REAL NOT NULL,
  end_seconds REAL NOT NULL,
  text_raw TEXT NOT NULL
);

CREATE UNIQUE INDEX idx_subtitles_unique
ON subtitles(idx, imdb_id_int, start_seconds, end_seconds);

