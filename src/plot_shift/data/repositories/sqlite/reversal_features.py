from __future__ import annotations

import sqlite3

from plot_shift.data.models.reversal_features import ReversalFeatures
from plot_shift.data.repository import ReversalFeaturesRepository


class ReversalFeaturesSqliteRepository(ReversalFeaturesRepository):
    """SQLite-backed repository for reversal features.

    Column mapping (DB → Python):
        scorer_name      ← scorer_name   (renamed from 'model' in migration 20260926210000)
        trend_window_size← trend_window_size (renamed from 'prominence')
        window_duration  ← window_duration  (added in migration 20260926210000)
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._db_conn = conn
        self._db_conn.row_factory = sqlite3.Row

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _to_row(
        f: ReversalFeatures,
    ) -> tuple[int, str, str, int, float, int, int, int, float, float, str]:
        return (
            f.imdb_id_int,
            f.scorer_name,
            f.dimension,
            f.n_windows,
            f.window_duration,
            f.trend_window_size,
            f.series_length,
            f.n_reversals,
            f.mean_intensity,
            f.max_intensity,
            f.detector_name,
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ReversalFeatures:
        return ReversalFeatures(
            imdb_id_int=int(row["imdb_id_int"]),
            scorer_name=str(row["scorer_name"]),
            dimension=str(row["dimension"]),
            n_windows=int(row["n_windows"]) if row["n_windows"] is not None else 0,
            window_duration=float(row["window_duration"]),
            trend_window_size=int(row["trend_window_size"]),
            series_length=int(row["series_length"]),
            n_reversals=int(row["n_reversals"]),
            mean_intensity=float(row["mean_intensity"]),
            max_intensity=float(row["max_intensity"]),
            detector_name=str(row["detector_name"]),
        )

    # ------------------------------------------------------------------
    # ReversalFeaturesRepository interface
    # ------------------------------------------------------------------

    def upsert_many(self, features: list[ReversalFeatures]) -> None:
        if not features:
            return
        rows = [self._to_row(f) for f in features]
        self._db_conn.executemany(
            """
            INSERT INTO reversal_features
                (imdb_id_int, scorer_name, dimension, n_windows, window_duration,
                 trend_window_size, series_length, n_reversals, mean_intensity, max_intensity, detector_name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(imdb_id_int, scorer_name, detector_name, dimension) DO UPDATE SET
                n_windows         = excluded.n_windows,
                window_duration   = excluded.window_duration,
                trend_window_size = excluded.trend_window_size,
                series_length     = excluded.series_length,
                n_reversals       = excluded.n_reversals,
                mean_intensity    = excluded.mean_intensity,
                max_intensity     = excluded.max_intensity
            """,
            rows,
        )
        self._db_conn.commit()

    def list_all(
        self,
        scorer_name: str | None = None,
        dimension: str | None = None,
        detector_name: str | None = None,
    ) -> list[ReversalFeatures]:
        where_parts: list[str] = []
        args: list[object] = []

        if scorer_name is not None:
            where_parts.append("scorer_name = ?")
            args.append(scorer_name)
        if dimension is not None:
            where_parts.append("dimension = ?")
            args.append(dimension)
        if detector_name is not None:
            where_parts.append("detector_name = ?")
            args.append(detector_name)

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        rows = self._db_conn.execute(
            f"""
            SELECT imdb_id_int, scorer_name, dimension, n_windows, window_duration,
                   trend_window_size, series_length, n_reversals, mean_intensity, max_intensity, detector_name
            FROM reversal_features
            {where_clause}
            ORDER BY imdb_id_int, scorer_name, detector_name, dimension
            """,
            args,
        ).fetchall()
        return [self._from_row(r) for r in rows]

    def find(
        self,
        imdb_id_int: int,
        scorer_name: str,
        dimension: str,
        detector_name: str | None = None,
    ) -> ReversalFeatures | None:
        where = "imdb_id_int = ? AND scorer_name = ? AND dimension = ?"
        args: list[object] = [imdb_id_int, scorer_name, dimension]
        if detector_name is not None:
            where += " AND detector_name = ?"
            args.append(detector_name)
        row = self._db_conn.execute(
            f"""
            SELECT imdb_id_int, scorer_name, dimension, n_windows, window_duration,
                   trend_window_size, series_length, n_reversals, mean_intensity, max_intensity, detector_name
            FROM reversal_features
            WHERE {where}
            ORDER BY detector_name
            LIMIT 1
            """,
            args,
        ).fetchone()
        return self._from_row(row) if row is not None else None

    def delete_by_movie(self, imdb_id_int: int) -> None:
        self._db_conn.execute(
            "DELETE FROM reversal_features WHERE imdb_id_int = ?",
            (imdb_id_int,),
        )
        self._db_conn.commit()
