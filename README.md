# plot-shift

`plot-shift` is a thesis project for studying narrative sentiment patterns in movies.
This `main` branch currently focuses on data ingest: downloading metadata/subtitles
and processing subtitle files into SQLite.

## What is currently implemented on `main`

- Download raw IMDb files (`title.basics.tsv`, `title.ratings.tsv`)
- Download English subtitles from OpenSubtitles for catalog movies
- Parse `.srt` files and insert cleaned subtitle rows into SQLite
- Score subtitle sentences with VADER and persist results
- Score subtitle sentences with VAD and persist results
- Score subtitle sentences with a transformer model and persist results

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

### `score-vader`

Scores processed subtitle sentences with VADER and stores results in
`sentence_model_scores`.

```bash
uv run plot-shift score-vader \
  --db data/proceeded/data.db \
  --batch-size 1000 \
  --limit 100
```

Arguments:

- `--db`: SQLite DB path (default: `data/proceeded/data.db`)
- `--batch-size`: sentence score upsert batch size (default: `1000`)
- `--limit`: optional cap on valid movies to score (default: no limit)

### `score-vad`

Scores processed subtitle sentences with NRC-VAD and stores results in
`sentence_model_scores`.

```bash
uv run plot-shift score-vad \
  --db data/proceeded/data.db \
  --batch-size 1000 \
  --limit 100 \
  --lexicon-file data/raw/lexicons/vad_lexicon.txt
```

Arguments:

- `--db`: SQLite DB path (default: `data/proceeded/data.db`)
- `--batch-size`: sentence score upsert batch size (default: `1000`)
- `--limit`: optional cap on valid movies to score (default: no limit)
- `--lexicon-file`: path to VAD lexicon file

### `score-semantic`

Scores processed subtitle sentences with a Hugging Face transformer model and stores
results in `sentence_model_scores`.

Default model: `cardiffnlp/twitter-roberta-base-sentiment-latest` (free to use under
CC BY 4.0 with attribution).

```bash
uv sync --group semantic
uv run plot-shift score-semantic \
  --db data/proceeded/data.db \
  --batch-size 1000 \
  --limit 100 \
  --model-name cardiffnlp/twitter-roberta-base-sentiment-latest
```

Arguments:

- `--db`: SQLite DB path (default: `data/proceeded/data.db`)
- `--batch-size`: sentence score upsert batch size (default: `1000`)
- `--limit`: optional cap on valid movies to score (default: no limit)
- `--model-name`: Hugging Face model id for sequence classification

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
5. Score sentences with VADER:
   ```bash
   uv run plot-shift score-vader
   ```
6. Score sentences with VAD:
   ```bash
   uv run plot-shift score-vad --lexicon-file data/raw/lexicons/vad_lexicon.txt
   ```
7. Score sentences with transformer model:
   ```bash
   uv sync --group semantic
   uv run plot-shift score-semantic --model-name cardiffnlp/twitter-roberta-base-sentiment-latest
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

- reversal feature extraction
- evaluation/report generation
