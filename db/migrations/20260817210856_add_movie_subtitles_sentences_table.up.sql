CREATE TABLE IF NOT EXISTS movie_subtitles_sentences(
  id INTEGER PRIMARY KEY,
  imdb_id_int INTEGER NOT NULL,
  content TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_imdb_id ON movie_subtitles_sentences(imdb_id_int);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sentences_unique
ON movie_subtitles_sentences(imdb_id_int, content);

