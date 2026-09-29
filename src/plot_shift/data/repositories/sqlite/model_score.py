from __future__ import annotations

import sqlite3

from plot_shift.data.models import ModelScore
from plot_shift.data.repository import ModelScoresRepository


class ModelScoreSqliteRepository(ModelScoresRepository):
    def __init__(self, conn: sqlite3.Connection):
        self._db_conn = conn
        self._db_conn.row_factory = sqlite3.Row

    @staticmethod
    def _to_row(
        score: ModelScore,
    ) -> tuple[int, int | None, int | None, int, int, str, str, str, float]:
        return (
            score.imdb_id_int,
            score.from_segment_idx,
            score.to_segment_idx,
            score.window_idx,
            score.total_windows,
            score.scorer_name,
            score.scorer_kind,
            score.dimension,
            score.score,
        )

    @staticmethod
    def _row_to_model_score(row: sqlite3.Row) -> ModelScore:
        return ModelScore(
            imdb_id_int=int(row["imdb_id_int"]),
            from_segment_idx=row["from_segment_idx"],
            to_segment_idx=row["to_segment_idx"],
            window_idx=int(row["window_idx"]),
            total_windows=int(row["total_windows"]),
            scorer_name=str(row["scorer_name"]),
            scorer_kind=str(row["scorer_kind"]),
            dimension=str(row["dimension"]),
            score=float(row["score"]),
        )

    def insert_many(self, scores: list[ModelScore]) -> None:
        if not scores:
            return

        rows = [self._to_row(score) for score in scores]
        self._db_conn.executemany(
            """
            INSERT INTO model_scores
                (imdb_id_int, from_segment_idx, to_segment_idx, window_idx, total_windows,
                 scorer_name, scorer_kind, dimension, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(imdb_id_int, window_idx, scorer_name, dimension) DO UPDATE SET
                score = excluded.score,
                from_segment_idx = excluded.from_segment_idx,
                to_segment_idx = excluded.to_segment_idx,
                total_windows = excluded.total_windows
            """,
            rows,
        )
        self._db_conn.commit()

    def delete_movie_model(self, imdb_id_int: int, scorer_name: str) -> None:
        self._db_conn.execute(
            "DELETE FROM model_scores WHERE imdb_id_int = ? AND scorer_name = ?",
            (imdb_id_int, scorer_name),
        )
        self._db_conn.commit()

    def list_groups(
        self,
        scorer_name: str | None = None,
        dimension: str | None = None,
        limit_movies: int | None = None,
    ) -> list[tuple[int, str, str]]:
        where_parts: list[str] = []
        args: list[object] = []

        if limit_movies is not None:
            where_parts.append(
                "imdb_id_int IN ("
                "SELECT DISTINCT imdb_id_int FROM model_scores "
                "ORDER BY imdb_id_int LIMIT ?)"
            )
            args.append(limit_movies)
        if scorer_name is not None:
            where_parts.append("lower(scorer_name) = ?")
            args.append(scorer_name.lower())
        if dimension is not None:
            where_parts.append("dimension = ?")
            args.append(dimension)

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        rows = self._db_conn.execute(
            f"""
            SELECT DISTINCT imdb_id_int, scorer_name, dimension
            FROM model_scores
            {where_clause}
            ORDER BY imdb_id_int, scorer_name, dimension
            """,
            args,
        ).fetchall()
        return [(int(r["imdb_id_int"]), str(r["scorer_name"]), str(r["dimension"])) for r in rows]

    def list_windowed(
        self,
        imdb_id_int: int,
        scorer_name: str,
        dimension: str,
    ) -> list[ModelScore]:
        rows = self._db_conn.execute(
            """
            SELECT imdb_id_int, from_segment_idx, to_segment_idx, window_idx,
                   total_windows, scorer_name, scorer_kind, dimension, score
            FROM model_scores
            WHERE imdb_id_int = ? AND scorer_name = ? AND dimension = ?
            ORDER BY window_idx ASC
            """,
            (imdb_id_int, scorer_name, dimension),
        ).fetchall()
        return [self._row_to_model_score(r) for r in rows]
