# plot-shift

`plot-shift` is a thesis project for studying narrative sentiment patterns in movies.
This `main` branch currently focuses on data ingest: downloading metadata/subtitles
and processing subtitle files into SQLite.

## What is currently implemented on `main`

- Download raw IMDb files (`title.basics.tsv`, `title.ratings.tsv`)
- Download English subtitles from OpenSubtitles for catalog movies
- Parse `.srt` files and insert cleaned subtitle rows into SQLite

Scoring, semantic modeling, and evaluation commands are not part of `main` yet.

## Requirements

- Python `>=3.14`
- [`uv`](https://docs.astral.sh/uv/) for environment and command execution
- `bash`, `curl`, `wget`, `gunzip` (used by IMDb download script)
- Optional: `just` + `golang-migrate` for DB migrations

## Setup

```bash
uv sync
```

Create a `.env` file in project root for OpenSubtitles credentials:

```env
OPEN_SUBTITLE_API_KEY=...
OPEN_SUBTITLE_USER_AGENT=...
OPEN_SUBTITLE_USERNAME=...
OPEN_SUBTITLE_PASSWORD=...
```

## CLI quickstart

```bash
uv run plot-shift --help
```

You can also run:

```bash
uv run python -m plot_shift --help
```

## Commands

### `fetch-imdb`

Downloads IMDb raw datasets into `data/raw/` by running `download_prerequire_raw.sh`.

```bash
uv run plot-shift fetch-imdb
```

### `download-subs`

Downloads missing English subtitles for movies found in your DB catalog (`movies_meta`)
and stores subtitle files in `data/raw/subtitles`.

```bash
uv run plot-shift download-subs \
  --db data/proceeded/data.db \
  --subtitles-dir data/raw/subtitles \
  --limit 100
```

Arguments:

- `--db`: SQLite DB path (default: `data/proceeded/data.db`)
- `--subtitles-dir`: subtitle output directory (default: `data/raw/subtitles`)
- `--limit`: optional cap for batch downloads (default: no limit)

### `process-subs`

Parses downloaded subtitle files and inserts cleaned rows into `movie_subtitles_meta`.

```bash
uv run plot-shift process-subs \
  --db data/proceeded/data.db \
  --subtitles-dir data/raw/subtitles \
  --batch-size 500
```

Arguments:

- `--db`: SQLite DB path (default: `data/proceeded/data.db`)
- `--subtitles-dir`: directory containing `.srt` files (default: `data/raw/subtitles`)
- `--batch-size`: insert batch size (default: `500`)

## Minimal workflow on `main`

1. Download IMDb files:
   ```bash
   uv run plot-shift fetch-imdb
   ```
2. Build/populate your `movies_meta` catalog (currently done via your notebook flow).
3. Download subtitles for that catalog:
   ```bash
   uv run plot-shift download-subs
   ```
4. Parse and insert subtitle content:
   ```bash
   uv run plot-shift process-subs
   ```

## Database and migrations

Use `just` targets for schema migrations (do not use Python CLI for migrations):

```bash
just mig-up
just mig-down
just mig-ver
```

## Development checks

```bash
uv run ruff check src
uv run mypy src
uv run pytest
```

## Next planned CLI expansions

As the thesis implementation continues, additional commands can be added for:

- sentiment scoring
- reversal feature extraction
- semantic scoring import/export
- evaluation/report generation
