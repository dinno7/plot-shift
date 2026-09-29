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

Parses downloaded subtitle files. Each subtitle _cue_ is cleaned and
sentence-tokenized on its own (never joined into one big string first), so
every resulting segment keeps its cue's real start/end timestamp. Segments
are inserted into `subtitle_segments`; aggregate stats (word/segment counts,
real duration, validity) go into `movie_subtitles`.

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
`model_scores`.

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
`model_scores`.

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
results in `model_scores`.

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

### `export-colab-data`

Exports narrative windows to CSV for remote scoring in Google Colab (or any
cloud GPU environment).  Each row is one temporal window of a movie — the same
unit that the local scorers operate on — so imported results land directly in
`model_scores` without any re-aggregation.

```bash
uv run plot-shift export-colab-data \
  --db data/proceeded/data.db \
  --out-csv data/proceeded/colab_input.csv \
  --n-windows 100 \
  --window-seconds 300 \
  --limit 100
```

Arguments:

- `--db`: SQLite DB path (default: `data/proceeded/data.db`)
- `--out-csv`: output CSV path (default: `data/proceeded/colab_input.csv`)
- `--n-windows`: equal-width windows per movie (default: `100`)
- `--window-seconds`: window width in seconds (default: `300`)
- `--limit`: optional cap on movies to export (default: no limit)

Output CSV columns: `imdb_id_int`, `window_idx`, `total_windows`,
`from_segment_idx`, `to_segment_idx`, `window_text`

### `import-colab-scores`

Imports the scored CSV produced by `notebooks/colab_scorer.ipynb` into
`model_scores`.  For each `(imdb_id_int, scorer_name)` pair found in the
file, any pre-existing rows are deleted first so re-runs are idempotent.

```bash
uv run plot-shift import-colab-scores \
  --db data/proceeded/data.db \
  --csv-path data/proceeded/colab_scores.csv \
  --batch-size 1000
```

Arguments:

- `--db`: SQLite DB path (default: `data/proceeded/data.db`)
- `--csv-path`: scored CSV from Colab (**required**)
- `--batch-size`: rows per DB insert batch (default: `1000`)

Required CSV columns: `imdb_id_int`, `window_idx`, `total_windows`,
`from_segment_idx`, `to_segment_idx`, `scorer_name`, `scorer_kind`,
`dimension`, `score`

### Colab Scoring Notebook

Use `notebooks/colab_scorer.ipynb` when your local machine cannot run
heavyweight transformer models (e.g. PERT-EmoPair, which needs a GPU and a
pretrained weights file).

**Round-trip**

1. Export windows locally:
   ```bash
   uv run plot-shift export-colab-data --out-csv data/proceeded/colab_input.csv
   ```
2. Upload `colab_input.csv` to Colab (or mount from Google Drive).
3. Open `notebooks/colab_scorer.ipynb`, set `SCORER` and paths in the
   *Configuration* cell, then run all cells.
4. Download `colab_scores.csv` from Colab.
5. Import locally:
   ```bash
   uv run plot-shift import-colab-scores --csv-path data/proceeded/colab_scores.csv
   ```

**Supported scorers in the notebook**

| `SCORER` value | Model | Dimensions |
|---|---|---|
| `pert_emopar` (default) | RoBERTa-large VAD regressor — upload weights to `/content/pert_emopar_weights.pt` | valence, arousal, dominance |
| `cardiffnlp` | `cardiffnlp/twitter-roberta-base-sentiment-latest` — downloaded automatically | valence |

## Project flow

1. Build movie catalog in `movies_meta`.
2. Download subtitle files from OpenSubtitles.
3. Process `.srt` files into timestamped `subtitle_segments` (one row per
   cleaned, sentence-tokenized cue; each keeps its cue's real start/end).
4. Score segments with VADER and VAD locally.
5. Score segments semantically:
   - local with `score-semantic`, or
   - cloud with `export-colab-data` → `notebooks/colab_scorer.ipynb` → `import-colab-scores`.
6. `extract-reversals` buckets each movie's scored segments into a fixed
   number of equal-width, real-time windows (`--n-windows`, default 100 —
   same idea as Knight et al.'s fixed window count, so movies of any length
   are comparable), then finds peak/trough reversals on that windowed
   series, once per model/dimension.
7. `evaluate-models` / `report-snapshot` correlate reversal features
   (count, mean/max intensity) against IMDb rating, per model and dimension,
   so VADER (1D), NRC-VAD (3D), and the semantic model can be compared on
   the same footing.

### Adding a new scoring model

Implement the `SentimentScorer` protocol (`src/plot_shift/sentiment/base.py`)
and add one entry to `_SCORER_FACTORIES` in
`src/plot_shift/sentiment/registry.py`. It's then automatically available as
`--model <name>` on `score-model` and appears in `list_supported_scorer_strategies()`.
No other pipeline code needs to change: scoring, windowing, and reversal
extraction all key off of `(imdb_id_int, segment_idx, model, dimension)`.

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
7. Score sentences with transformer model (local):
   ```bash
   uv sync --group semantic
   uv run plot-shift score-semantic --model-name cardiffnlp/twitter-roberta-base-sentiment-latest
   ```
8. If local scoring is too heavy, use the Colab notebook instead:
   ```bash
   uv run plot-shift export-colab-data --out-csv data/proceeded/colab_input.csv
   # open notebooks/colab_scorer.ipynb in Colab, run all cells, download colab_scores.csv
   ```
9. Import Colab scores:
   ```bash
   uv run plot-shift import-colab-scores --csv-path data/proceeded/colab_scores.csv
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
