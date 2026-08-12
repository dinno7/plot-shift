import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple, TypedDict


class PlotShiftSqliteDB:
    def __init__(self, dbpath: str):
        self.db_conn = sqlite3.connect(dbpath)
        self.movies_meta = MovieMetaSqliteRepository(self.db_conn)
        self.downloaded_subtitles = DownloadedSubtitleSqliteRepository(self.db_conn)

    def __delete__(self, instance):
        self.db_conn.close()


@dataclass
class MovieMeta:
    """Mirrors the movies_meta table schema for type-safe access & autosuggestion."""

    imdb_id: str
    average_rating: float
    num_votes: int
    title_type: str
    primary_title: str
    original_title: str
    start_year: int
    runtime_minutes: int
    id: Optional[int] = None
    imdb_id_int: Optional[int] = None
    genres: Optional[str] = None


class MovieMetaSqliteRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.db_conn = conn

    def init_table(self):
        self.db_conn.execute("""CREATE TABLE movies_meta(
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    imdb_id TEXT NOT NULL,
                                    imdb_id_int INTEGER GENERATED ALWAYS AS (CAST(SUBSTR(imdb_id, 3) AS INTEGER)),
                                    average_rating REAL NOT NULL,
                                    num_votes INTEGER NOT NULL,
                                    title_type TEXT NOT NULL,
                                    primary_title TEXT NOT NULL,
                                    original_title TEXT NOT NULL,
                                    start_year INTEGER NOT NULL,
                                    runtime_minutes INTEGER NOT NULL,
                                    genres TEXT
                                );
        """)

    def drop_table(self):
        self.db_conn.execute("DROP TABLE IF EXISTS movies_meta;")

    def fresh_table(self):
        self.drop_table()
        self.init_table()

    def insert_many(
        self,
        movies_meta_list: List[MovieMeta],
    ):

        cursor = self.db_conn.cursor()
        query = "INSERT INTO movies_meta (imdb_id, average_rating, num_votes, primary_title, original_title, runtime_minutes, genres, title_type, start_year) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
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
        cursor.executemany(query, data)
        self.db_conn.commit()
        cursor.close()

    def get_all(self) -> List[MovieMeta]:
        """
        Fetches all rows from movies_meta.

        Returns:
            list[MovieMeta]: Type-safe list of movie metadata dictionaries.
                             IDE autosuggestion works on each item's keys.
        """
        cursor = self.db_conn.execute(
            "SELECT * FROM movies_meta ORDER BY num_votes desc;"
        )
        # sqlite3.Row supports dict() conversion which satisfies TypedDict
        fetched = cursor.fetchall()
        result = [
            MovieMeta(
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
            for row in fetched
        ]
        cursor.close()
        return result


@dataclass
class DownloadedSubtitle:
    subtitle_id: str
    download_count: int
    new_download_count: int
    file_id: int
    imdb_id_int: int
    file_name_on_disk: str
    url: str
    id: Optional[int] = None
    language: Optional[str] = None
    upload_date: Optional[str] = None
    fetched_at: Optional[datetime] = None
    dump_json: Optional[str] = None


class DownloadedSubtitleSqliteRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.db_conn = conn

    def init_table(self):
        self.db_conn.execute("""CREATE TABLE IF NOT EXISTS downloaded_subtitles(
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    imdb_id_int INTEGER NOT NULL,
                                    file_id INTEGER NOT NULL,
                                    file_name_on_disk TEXT NOT NULL,
                                    subtitle_id TEXT NOT NULL,
                                    download_count INTEGER NOT NULL,
                                    new_download_count INTEGER NOT NULL,
                                    language TEXT,
                                    upload_date TEXT,
                                    url TEXT,
                                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                    dump_json TEXT
                                );
        """)

    # def drop_table(self):
    #     self.db_conn.execute("DROP TABLE IF EXISTS downloaded_subtitles;")

    # def fresh_table(self):
    #     self.drop_table()
    #     self.init_table()

    def insert_one(self, subtitle: DownloadedSubtitle) -> int:
        """
        Insert a downloaded subtitle into the database.
        Returns the ID of the inserted row.
        """
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO downloaded_subtitles 
            (imdb_id_int, file_id, file_name_on_disk, subtitle_id, download_count, new_download_count, 
            language, upload_date, url, dump_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                subtitle.imdb_id_int,
                subtitle.file_id,
                subtitle.file_name_on_disk,
                subtitle.subtitle_id,
                subtitle.download_count,
                subtitle.new_download_count,
                subtitle.language,
                subtitle.upload_date,
                subtitle.url,
                subtitle.dump_json,
            ),
        )

        last_id = cursor.lastrowid
        self.db_conn.commit()
        cursor.close()
        return last_id

    def get_all(self) -> List[DownloadedSubtitle]:
        cursor = self.db_conn.execute("SELECT * FROM downloaded_subtitles;")
        fetched = cursor.fetchall()
        result = [
            DownloadedSubtitle(
                id=row[0],
                imdb_id_int=row[1],
                file_id=row[2],
                file_name_on_disk=row[3],
                subtitle_id=row[4],
                download_count=row[5],
                new_download_count=row[6],
                language=row[7],
                upload_date=row[8],
                url=row[9],
                fetched_at=datetime.fromisoformat(row[10]) if row[10] else None,
                dump_json=row[11],
            )
            for row in fetched
        ]
        cursor.close()
        return result
