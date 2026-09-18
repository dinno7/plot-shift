CREATE TABLE IF NOT EXISTS movie_subtitles (
    imdb_id_int integer PRIMARY KEY,
    words_count integer,
    sentences_count integer,
    duration_minutes integer,
    duration_seconds real,
    is_valid boolean
);

CREATE INDEX IF NOT EXISTS idx_movie_subtitles_imdb_id ON movie_subtitles (imdb_id_int);

CREATE TABLE IF NOT EXISTS subtitle_segments (
    id integer PRIMARY KEY,
    imdb_id_int integer NOT NULL,
    segment_idx integer NOT NULL,
    start_seconds real NOT NULL,
    end_seconds real NOT NULL,
    content text NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_subtitle_segments_imdb_id ON subtitle_segments (imdb_id_int);

CREATE UNIQUE INDEX IF NOT EXISTS idx_subtitle_segments_unique ON subtitle_segments (imdb_id_int, segment_idx);

