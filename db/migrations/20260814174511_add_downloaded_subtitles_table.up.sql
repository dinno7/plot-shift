CREATE TABLE IF NOT EXISTS downloaded_subtitles(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  imdb_id_int INTEGER NOT NULL,
  file_id INTEGER NOT NULL,
  file_name_on_disk TEXT NOT NULL,
  subtitle_id TEXT NOT NULL,
  download_count INTEGER NOT NULL,
  new_download_count INTEGER NOT NULL,
  language TEXT,
  upload_date TEXT,
  url TEXT,
  fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  dump_json TEXT
  );
