CREATE TABLE IF NOT EXISTS movies_meta (
    id integer PRIMARY KEY AUTOINCREMENT,
    imdb_id text NOT NULL,
    imdb_id_int integer GENERATED ALWAYS AS (CAST(SUBSTR(imdb_id, 3) AS integer)),
    average_rating real NOT NULL,
    num_votes integer NOT NULL,
    title_type text NOT NULL,
    primary_title text NOT NULL,
    original_title text NOT NULL,
    start_year integer NOT NULL,
    runtime_minutes integer NOT NULL,
    genres text
);
