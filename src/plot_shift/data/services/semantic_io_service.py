from __future__ import annotations

import csv
from pathlib import Path

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.models import ModelScore


def export_sentences_for_semantic(
    db_path: str = "data/proceeded/data.db",
    out_csv: str = "data/proceeded/semantic_input.csv",
    limit: int | None = None,
) -> dict[str, int | str]:
    with PlotShiftSqliteDB(db_path) as db:
        imdb_ids = db.movie_subtitles.list_valid_imdb_ids()
        if limit is not None:
            imdb_ids = imdb_ids[:limit]

        out_path = Path(out_csv)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        rows_written = 0
        with out_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["imdb_id_int", "segment_idx", "sentence_text"])
            for imdb_id_int in imdb_ids:
                sentences = db.movie_subtitles.list_sentences_by_imdb_id(imdb_id_int)
                for segment_idx, sentence in enumerate(sentences):
                    writer.writerow([imdb_id_int, segment_idx, sentence])
                    rows_written += 1

        return {
            "movies_exported": len(imdb_ids),
            "sentences_exported": rows_written,
            "out_csv": str(out_path),
        }


def import_semantic_scores(
    csv_path: str,
    db_path: str = "data/proceeded/data.db",
    batch_size: int = 1000,
    default_model: str = "semantic:cardiffnlp/twitter-roberta-base-sentiment-latest",
    default_dimension: str = "valence",
) -> dict[str, int | str]:
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
            required = {"imdb_id_int", "segment_idx", "score"}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise ValueError(
                    "CSV must include headers: imdb_id_int,segment_idx,score "
                    "(optional: model,dimension)."
                )

            for row in reader:
                rows_read += 1
                imdb_id_int = int(row["imdb_id_int"])
                window_idx = int(row["window_idx"])
                total_windows = int(row["total_windows"])
                from_segment_idx = int(row["from_segment_idx"])
                to_segment_idx = int(row["to_segment_idx"])
                model = (row.get("model") or default_model).strip()
                dimension = (row.get("dimension") or default_dimension).strip()
                score = float(row["score"])

                clear_key = (imdb_id_int, model)
                if clear_key not in cleared_pairs:
                    db.model_scores.delete_movie_model(imdb_id_int, model)
                    cleared_pairs.add(clear_key)

                buffer.append(
                    ModelScore(
                        imdb_id_int=imdb_id_int,
                        window_idx=window_idx,
                        total_windows=total_windows,
                        from_segment_idx=from_segment_idx,
                        to_segment_idx=to_segment_idx,
                        model=model,
                        dimension=dimension,
                        score=score,
                    )
                )

                if len(buffer) >= batch_size:
                    db.model_scores.insert_many(buffer)
                    rows_written += len(buffer)
                    buffer.clear()

        if buffer:
            db.model_scores.insert_many(buffer)
            rows_written += len(buffer)
            buffer.clear()

        return {
            "rows_read": rows_read,
            "rows_written": rows_written,
            "unique_movie_model_pairs_replaced": len(cleared_pairs),
            "in_csv": str(in_path),
        }
