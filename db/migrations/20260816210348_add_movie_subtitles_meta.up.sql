CREATE TABLE IF NOT EXISTS movie_subtitles_meta (
  imdb_id_int INTEGER PRIMARY KEY,
  words_count INTEGER,
  sentences_count INTEGER,
  duration_minutes INTEGER,
  is_valid BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_movie_subtitles_meta_imdb_id ON movie_subtitles_meta(imdb_id_int);
