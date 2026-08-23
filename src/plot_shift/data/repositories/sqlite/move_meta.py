import sqlite3
from typing import Any

from plot_shift.data.models import MovieMeta
from plot_shift.data.repository import MovieMetaRepository


class MovieMetaSqliteRepository(MovieMetaRepository):
    def __init__(self, conn: sqlite3.Connection):
        self.db_conn = conn

    _INSERT_QUERY = """
        INSERT INTO movies_meta
        (imdb_id, average_rating, num_votes, primary_title, original_title,
         runtime_minutes, genres, title_type, start_year)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    _SELECT_ALL_QUERY = "SELECT * FROM movies_meta ORDER BY num_votes DESC"

    def insert_many(self, movies_meta_list: list[MovieMeta]) -> None:
        data = [
            (
                row.imdb_id,
                row.average_rating,
                row.num_votes,
                row.primary_title,
                row.original_title,
                row.runtime_minutes,
                row.genres,
                row.title_type,
                row.start_year,
            )
            for row in movies_meta_list
        ]
        cursor = self.db_conn.cursor()
        try:
            cursor.executemany(self._INSERT_QUERY, data)
            self.db_conn.commit()
        finally:
            cursor.close()

    def get_all(self) -> list[MovieMeta]:
        """Fetches all movies ordered by vote count descending."""
        cursor = self.db_conn.execute(self._SELECT_ALL_QUERY)
        try:
            return [self._row_to_movie(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    @staticmethod
    def _row_to_movie(row: tuple[Any, ...]) -> MovieMeta:
        """Convert a raw DB row to a MovieMeta dataclass."""
        return MovieMeta(
            id=row[0],
            imdb_id=row[1],
            imdb_id_int=row[2],
            average_rating=row[3],
            num_votes=row[4],
            title_type=row[5],
            primary_title=row[6],
            original_title=row[7],
            start_year=row[8],
            runtime_minutes=row[9],
            genres=row[10],
        )
