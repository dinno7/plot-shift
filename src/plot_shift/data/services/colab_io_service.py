"""Export/import helpers for the Google Colab remote-scoring workflow.

Colab round-trip
----------------
1. Local:  ``plot-shift export-colab-data`` → ``colab_input.csv``
2. Colab:  ``notebooks/colab_scorer.ipynb`` scores every row with a heavy
           transformer model and writes ``colab_scores.csv``.
3. Local:  ``plot-shift import-colab-scores --csv-path colab_scores.csv``
           persists the results through the repository layer.

CSV schemas
-----------
Input  (export output / colab input):
    imdb_id_int, window_idx, total_windows,
    from_segment_idx, to_segment_idx, window_text

Output (colab output / import input):
    imdb_id_int, window_idx, total_windows,
    from_segment_idx, to_segment_idx,
    scorer_name, scorer_kind, dimension, score
"""

from __future__ import annotations

import csv
import logging
from datetime import timedelta
from pathlib import Path

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.models import ModelScore
from plot_shift.windows import create_window_generator

logger = logging.getLogger(__name__)

_EXPORT_HEADERS = [
    "imdb_id_int",
    "window_idx",
    "total_windows",
    "from_segment_idx",
    "to_segment_idx",
    "window_text",
]

_IMPORT_REQUIRED = {
    "imdb_id_int",
    "window_idx",
    "total_windows",
    "from_segment_idx",
    "to_segment_idx",
    "scorer_name",
    "scorer_kind",
    "dimension",
    "score",
}


def export_windows_for_colab(
    db_path: str = "data/proceeded/data.db",
    out_csv: str = "data/proceeded/colab_input.csv",
    n_windows: int = 100,
    window_seconds: int = 300,
    windower: str = "fixed-width-duration",
    limit: int | None = None,
) -> dict[str, int | str]:
    """Export narrative windows to CSV for remote scoring in Google Colab.

    Each row is one temporal window of a movie.  The Colab scoring notebook
    reads this file, scores each ``window_text``, and writes a companion CSV
    that ``import_colab_scores`` can load back into the database.

    Args:
        db_path:        Path to the SQLite database.
        out_csv:        Destination CSV path.
        n_windows:      Number of windows per movie for ``fixed-width-duration``.
        window_seconds: Width of each window in seconds.
        windower:    ``fixed-width-duration`` or ``fixed-duration``.
        limit:          Optional cap on the number of movies to export.

    Returns:
        Summary dict with ``movies_exported``, ``windows_exported``,
        and ``out_csv`` keys.
    """
    window_generator = create_window_generator(
        windower,
        window_duration=timedelta(seconds=window_seconds),
        n_windows=n_windows,
    )

    with PlotShiftSqliteDB(db_path) as db:
        imdb_ids = db.movie_subtitles.list_valid_imdb_ids(limit)
        if limit is not None:
            imdb_ids = imdb_ids[:limit]

        out_path = Path(out_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        movies_exported = 0
        windows_exported = 0

        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(_EXPORT_HEADERS)

            for imdb_id_int in imdb_ids:
                movie = db.movie_subtitles.find_by_imdb_id(imdb_id_int)
                if movie is None:
                    logger.warning("Movie %d not found in DB, skipping.", imdb_id_int)
                    continue

                windows = window_generator.generate(movie)
                total = len(windows)

                for window in windows:
                    writer.writerow(
                        [
                            imdb_id_int,
                            window.index,
                            total,
                            window.from_segment_idx,
                            window.to_segment_idx,
                            window.text,
                        ]
                    )
                    windows_exported += 1

                movies_exported += 1
                logger.info("Exported %d windows for movie %d.", total, imdb_id_int)

    return {
        "movies_exported": movies_exported,
        "windows_exported": windows_exported,
        "out_csv": str(out_path),
    }


def import_colab_scores(
    csv_path: str,
    db_path: str = "data/proceeded/data.db",
    batch_size: int = 1000,
) -> dict[str, int | str]:
    """Import window-level scores produced by the Colab scoring notebook.

    All columns must be present in the CSV (see module docstring).  For each
    (imdb_id_int, scorer_name) pair encountered, any pre-existing rows are
    deleted before the new ones are inserted so re-runs are idempotent.

    Args:
        csv_path:   Path to the scored CSV file from Colab.
        db_path:    Path to the SQLite database.
        batch_size: Number of rows to insert per DB round-trip.

    Returns:
        Summary dict with ``rows_read``, ``rows_written``,
        ``unique_movie_scorer_pairs_replaced``, and ``in_csv`` keys.

    Raises:
        FileNotFoundError: If ``csv_path`` does not exist.
        ValueError:        If the CSV is missing required columns.
    """
    in_path = Path(csv_path)
    if not in_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    with PlotShiftSqliteDB(db_path) as db:
        buffer: list[ModelScore] = []
        rows_read = 0
        rows_written = 0
        cleared_pairs: set[tuple[int, str]] = set()

        with in_path.open("r", newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            actual_columns = set(reader.fieldnames or [])
            missing = _IMPORT_REQUIRED - actual_columns
            if missing:
                raise ValueError(
                    f"CSV is missing required columns: {sorted(missing)}. "
                    f"Expected all of: {sorted(_IMPORT_REQUIRED)}"
                )

            for row in reader:
                rows_read += 1
                imdb_id_int = int(row["imdb_id_int"])
                scorer_name = row["scorer_name"].strip()

                # Wipe previous scores for this (movie, scorer) pair once.
                clear_key = (imdb_id_int, scorer_name)
                if clear_key not in cleared_pairs:
                    db.model_scores.delete_movie_model(imdb_id_int, scorer_name)
                    cleared_pairs.add(clear_key)

                from_seg = row["from_segment_idx"].strip()
                to_seg = row["to_segment_idx"].strip()

                buffer.append(
                    ModelScore(
                        imdb_id_int=imdb_id_int,
                        window_idx=int(row["window_idx"]),
                        total_windows=int(row["total_windows"]),
                        from_segment_idx=int(float(from_seg)) if from_seg else None,
                        to_segment_idx=int(float(to_seg)) if to_seg else None,
                        scorer_name=scorer_name,
                        scorer_kind=row["scorer_kind"].strip(),
                        dimension=row["dimension"].strip(),
                        score=float(row["score"]),
                    )
                )

                if len(buffer) >= batch_size:
                    db.model_scores.insert_many(buffer)
                    rows_written += len(buffer)
                    buffer.clear()

        if buffer:
            db.model_scores.insert_many(buffer)
            rows_written += len(buffer)

    return {
        "rows_read": rows_read,
        "rows_written": rows_written,
        "unique_movie_scorer_pairs_replaced": len(cleared_pairs),
        "in_csv": str(in_path),
    }
