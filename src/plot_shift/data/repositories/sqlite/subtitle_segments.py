import sqlite3
from datetime import timedelta

from plot_shift.data.models.subtitle_segment import SubtitleSegment
from plot_shift.data.repository import SubtitleSegmentsRepository


class SubtitleSegmentsSqliteRepository(SubtitleSegmentsRepository):
    """SQLite-backed implementation of SubtitleSegmentsRepository."""

    _UPSERT_SQL = """
        INSERT INTO subtitle_segments (imdb_id_int, segment_idx, start_seconds, end_seconds, content)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(imdb_id_int, segment_idx) DO UPDATE SET
            start_seconds = excluded.start_seconds,
            end_seconds   = excluded.end_seconds,
            content       = excluded.content;
    """

    _SELECT_BY_IMDB_SQL = """
        SELECT id, imdb_id_int, segment_idx, start_seconds, end_seconds, content
        FROM subtitle_segments
        WHERE imdb_id_int = ?
        ORDER BY segment_idx;
    """

    _DELETE_BY_IMDB_SQL = "DELETE FROM subtitle_segments WHERE imdb_id_int = ?;"

    def __init__(self, conn: sqlite3.Connection) -> None:
        conn.row_factory = sqlite3.Row
        # Enable WAL mode for better concurrent read performance
        conn.execute("PRAGMA journal_mode=WAL;")
        self._conn = conn
        self._conn.close()

    @staticmethod
    def _to_row(segment: SubtitleSegment) -> tuple:
        """Convert domain object to DB parameter tuple."""
        return (
            segment.imdb_id_int,
            segment.segment_idx,
            segment.start.total_seconds(),
            segment.end.total_seconds(),
            segment.content,
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> SubtitleSegment:
        """Convert DB row to domain object."""
        return SubtitleSegment(
            id=row["id"],
            imdb_id_int=row["imdb_id_int"],
            segment_idx=row["segment_idx"],
            start=timedelta(seconds=row["start_seconds"]),
            end=timedelta(seconds=row["end_seconds"]),
            content=row["content"],
        )

    def upsert(self, segment: SubtitleSegment) -> None:
        self._conn.execute(self._UPSERT_SQL, self._to_row(segment))

    def upsert_many(self, segments: list[SubtitleSegment]) -> None:
        if not segments:
            return
        rows = [self._to_row(m) for m in segments]
        # executemany within a context manager ensures atomicity
        self._conn.executemany(self._UPSERT_SQL, rows)

    def find_by_imdb_id(self, imdb_id: int) -> list[SubtitleSegment]:
        cursor = self._conn.execute(self._SELECT_BY_IMDB_SQL, (imdb_id,))
        return [self._from_row(row) for row in cursor.fetchall()]

    def delete(self, imdb_id: int) -> None:
        self._conn.execute(self._DELETE_BY_IMDB_SQL, (imdb_id,))
