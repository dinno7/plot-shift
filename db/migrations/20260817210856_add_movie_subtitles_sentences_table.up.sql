CREATE TABLE IF NOT EXISTS movie_subtitles_sentences (
    id integer PRIMARY KEY,
    imdb_id_int integer NOT NULL,
    content text NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_imdb_id ON movie_subtitles_sentences (imdb_id_int);

CREATE UNIQUE INDEX IF NOT EXISTS idx_sentences_unique ON movie_subtitles_sentences (imdb_id_int, content);

