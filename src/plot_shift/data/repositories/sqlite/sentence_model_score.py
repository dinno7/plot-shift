from __future__ import annotations

import sqlite3

from plot_shift.data.models import SentenceModelScore
from plot_shift.data.repository import SentenceModelScoreRepository


class SentenceModelScoreSqliteRepository(SentenceModelScoreRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _to_row(score: SentenceModelScore) -> tuple[int, int, str, str, float]:
        return (
            score.imdb_id_int,
            score.sentence_idx,
            score.model,
            score.dimension,
            score.score,
        )

    def insert_many(self, scores: list[SentenceModelScore]) -> None:
        if not scores:
            return

        rows = [self._to_row(score) for score in scores]
        with self._get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO sentence_model_scores
                    (imdb_id_int, sentence_idx, model, dimension, score)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(imdb_id_int, sentence_idx, model, dimension) DO UPDATE SET
                    score = excluded.score
                """,
                rows,
            )
            conn.commit()

    def delete_movie_model(self, imdb_id_int: int, model: str) -> None:
        with self._get_connection() as conn:
            conn.execute(
                "DELETE FROM sentence_model_scores WHERE imdb_id_int = ? AND model = ?",
                (imdb_id_int, model),
            )
            conn.commit()
