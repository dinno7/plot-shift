CREATE TABLE IF NOT EXISTS subtitles_meta (
    id integer PRIMARY KEY AUTOINCREMENT,
    imdb_id_int integer NOT NULL,
    file_id integer NOT NULL,
    file_name_on_disk text NOT NULL,
    subtitle_id text NOT NULL,
    download_count integer NOT NULL,
    new_download_count integer NOT NULL,
    language TEXT
,
    upload_date text,
    url text,
    fetched_at timestamp DEFAULT CURRENT_TIMESTAMP,
    dump_json text
);

