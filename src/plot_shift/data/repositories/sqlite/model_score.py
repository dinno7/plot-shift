from __future__ import annotations

import sqlite3

from plot_shift.data.models import ModelScore
from plot_shift.data.repository import ModelScoresRepository


class ModelScoreSqliteRepository(ModelScoresRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._db_conn = conn

    @staticmethod
    def _to_row(score: ModelScore) -> tuple[int, int, int, int, int, str, str, float]:
        return (
            score.imdb_id_int,
            score.from_segment_idx,
            score.to_segment_idx,
            score.window_idx,
            score.total_windows,
            score.model,
            score.dimension,
            score.score,
        )

    def insert_many(self, scores: list[ModelScore]) -> None:
        if not scores:
            return

        rows = [self._to_row(score) for score in scores]
        self._db_conn.executemany(
            """
            INSERT INTO model_scores
                (imdb_id_int, from_segment_idx, to_segment_idx, window_idx, total_windows, model, dimension, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(imdb_id_int, window_idx, model, dimension) DO UPDATE SET
                score = excluded.score,
                from_segment_idx = excluded.from_segment_idx,
                to_segment_idx = excluded.to_segment_idx,
                total_windows = excluded.total_windows
            """,
            rows,
        )
        self._db_conn.commit()

    def delete_movie_model(self, imdb_id_int: int, model: str) -> None:
        self._db_conn.execute(
            "DELETE FROM model_scores WHERE imdb_id_int = ? AND model = ?",
            (imdb_id_int, model),
        )
        self._db_conn.commit()
