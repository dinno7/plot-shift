import sqlite3
from datetime import timedelta
from typing import Any

from plot_shift.data.models import Subtitle
from plot_shift.data.repository import SentencesRepository


class SubtitleSqliteRepository(SentencesRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.db_conn: sqlite3.Connection = conn

    def _row_to_entry(self, row: tuple[Any, ...]) -> Subtitle:
        """Convert a database row to a Subtitle dataclass."""
        return Subtitle(
            id=row[0],
            index=row[1],
            imdb_id_int=row[2],
            start=timedelta(seconds=row[3]),
            end=timedelta(seconds=row[4]),
            text_raw=row[5],
        )

    def insert_one(self, entry: Subtitle) -> int | None:
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            INSERT OR IGNORE INTO subtitles (idx, imdb_id_int, start_seconds, end_seconds, text_raw)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                entry.index,
                entry.imdb_id_int,
                entry.start.total_seconds(),
                entry.end.total_seconds(),
                entry.text_raw,
            ),
        )
        last_id = cursor.lastrowid
        self.db_conn.commit()
        cursor.close()
        return last_id

    def insert_many(self, entries: list[Subtitle]) -> None:
        cursor = self.db_conn.cursor()
        data = [
            (
                e.index,
                e.imdb_id_int,
                e.start.total_seconds(),
                e.end.total_seconds(),
                e.text_raw,
            )
            for e in entries
        ]
        cursor.executemany(
            """
            INSERT OR IGNORE INTO subtitles (idx, imdb_id_int, start_seconds, end_seconds, text_raw)
            VALUES (?, ?, ?, ?, ?)
            """,
            data,
        )
        self.db_conn.commit()
        cursor.close()

    def get_by_id(self, entry_id: int) -> Subtitle | None:
        cursor = self.db_conn.execute("SELECT * FROM subtitles WHERE id = ?", (entry_id,))
        row = cursor.fetchone()
        cursor.close()
        return self._row_to_entry(row) if row else None

    def get_by_imdb_id(self, imdb_id_int: int) -> list[Subtitle]:
        cursor = self.db_conn.execute(
            "SELECT * FROM subtitles WHERE imdb_id_int = ? ORDER BY idx ASC",
            (imdb_id_int,),
        )
        rows = cursor.fetchall()
        cursor.close()
        return [self._row_to_entry(row) for row in rows]
