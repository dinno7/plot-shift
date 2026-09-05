CREATE TABLE IF NOT EXISTS movie_subtitles_meta (
    imdb_id_int integer PRIMARY KEY,
    words_count integer,
    sentences_count integer,
    duration_minutes integer,
    is_valid boolean
);

CREATE INDEX IF NOT EXISTS idx_movie_subtitles_meta_imdb_id ON movie_subtitles_meta (imdb_id_int);

