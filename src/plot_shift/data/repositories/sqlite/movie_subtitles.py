from __future__ import annotations

import sqlite3
from datetime import timedelta

from plot_shift.data.models.movie_subtitle_meta import MovieSubtitle
from plot_shift.data.models.subtitle_segment import SubtitleSegment
from plot_shift.data.repository import MovieSubtitlesRepository
from plot_shift.data.utils import stop_words, tokenize_all_words


class MovieSubtitlesSqliteRepository(MovieSubtitlesRepository):
    """
    Repository for persisting and retrieving MovieSubtitlesMeta.

    Note: This repository stores the PROCESSED state of the meta.
    Raw subtitle text is not stored in these tables; only cleaned,
    timestamped segments and aggregate statistics are persisted.
    """

    def __init__(self, conn: sqlite3.Connection):
        self._db_conn = conn

    @staticmethod
    def _validate_processed(movie_sub: MovieSubtitle) -> None:
        if movie_sub.segments is None:
            raise ValueError(f"MovieSubtitles(imdb_id={movie_sub.imdb_id}) must have segments.")

    @staticmethod
    def _prepare_meta_row(meta: MovieSubtitle) -> tuple[int, int, int, int, float, bool]:
        duration_seconds = meta.duration.total_seconds()
        duration_minutes = int(duration_seconds // 60)
        return (
            meta.imdb_id,
            meta.words_count,
            meta.sentences_count,
            duration_minutes,
            duration_seconds,
            meta.is_valid,
        )

    @staticmethod
    def _prepare_segment_rows(
        meta: MovieSubtitle,
    ) -> list[tuple[int, int, float, float, str]]:
        return [
            (
                meta.imdb_id,
                segment.segment_idx,
                segment.start.total_seconds(),
                segment.end.total_seconds(),
                segment.content,
            )
            for segment in meta.segments
        ]

    def upsert(self, movie_sub: MovieSubtitle) -> None:
        """Persists processed MovieSubtitlesMeta and its segments."""
        self.upsert_many([movie_sub])

    def upsert_many(self, movie_subs: list[MovieSubtitle]) -> None:
        if not movie_subs:
            return

        # Validate ALL records before opening a transaction
        for sub in movie_subs:
            self._validate_processed(sub)
            cursor = self._db_conn.cursor()

            # Batch upsert meta records
            meta_rows = [self._prepare_meta_row(m) for m in movie_subs]
            cursor.executemany(
                """
                INSERT INTO movie_subtitles
                    (imdb_id_int, words_count, sentences_count, duration_minutes,
                     duration_seconds, is_valid)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(imdb_id_int) DO UPDATE SET
                    words_count = excluded.words_count,
                    sentences_count = excluded.sentences_count,
                    duration_minutes = excluded.duration_minutes,
                    duration_seconds = excluded.duration_seconds,
                    is_valid = excluded.is_valid
            """,
                meta_rows,
            )

            # Batch insert all new segments in one executemany call
            all_segments: list[tuple[int, int, float, float, str]] = []
            for sub in movie_subs:
                all_segments.extend(self._prepare_segment_rows(sub))

            if all_segments:
                cursor.executemany(
                    """INSERT INTO subtitle_segments
                            (imdb_id_int, segment_idx, start_seconds, end_seconds, content)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT (imdb_id_int, segment_idx) DO UPDATE SET
                        start_seconds = excluded.start_seconds,
                        end_seconds = excluded.end_seconds,
                        content = excluded.content
                    """,
                    all_segments,
                )

            self._db_conn.commit()

    def _load_segments(self, imdb_id: int) -> list[SubtitleSegment]:
        rows = self._db_conn.execute(
            """
            SELECT id, segment_idx, start_seconds, end_seconds, content
            FROM subtitle_segments
            WHERE imdb_id_int = ?
            ORDER BY segment_idx ASC
            """,
            (imdb_id,),
        ).fetchall()
        return [
            SubtitleSegment(
                id=row["id"],
                imdb_id_int=imdb_id,
                segment_idx=row["segment_idx"],
                start=timedelta(seconds=row["start_seconds"]),
                end=timedelta(seconds=row["end_seconds"]),
                content=row["content"],
            )
            for row in rows
        ]

    def find_by_imdb_id(self, imdb_id: int) -> MovieSubtitle | None:
        """
        Reconstructs a MovieSubtitlesMeta from the database.

        NOTE: The returned object has pre-computed statistics and cleaned,
        timestamped segments. The raw cue text is not stored, so it cannot
        be recovered here; re-parse the .srt file if needed.
        """
        row = self._db_conn.execute(
            "SELECT * FROM movie_subtitles WHERE imdb_id_int = ?", (imdb_id,)
        ).fetchone()

        if row is None:
            return None

        segments = self._load_segments(imdb_id)
        words: list[str] = []
        for segment in segments:
            tokens = tokenize_all_words(segment.content)
            words.extend(w for w in tokens if w not in stop_words)

        return MovieSubtitle(imdb_id=row["imdb_id_int"], words=words, segments=segments)

    def list_valid_imdb_ids(self) -> list[int]:
        rows = self._db_conn.execute(
            """
            SELECT imdb_id_int FROM movie_subtitles
            WHERE is_valid = 1
            ORDER BY imdb_id_int
            """
        ).fetchall()
        return [int(r["imdb_id_int"]) for r in rows]

    def list_sentences_by_imdb_id(self, imdb_id: int) -> list[str]:
        return [segment.content for segment in self.list_segments_by_imdb_id(imdb_id)]

    def list_segments_by_imdb_id(self, imdb_id: int) -> list[SubtitleSegment]:
        return self._load_segments(self._db_conn, imdb_id)

    def exists(self, imdb_id: int) -> bool:
        row = self._db_conn.execute(
            "SELECT 1 FROM movie_subtitles WHERE imdb_id_int = ?", (imdb_id,)
        ).fetchone()
        return row is not None

    def delete(self, imdb_id: int) -> None:
        self._db_conn.execute("DELETE FROM subtitle_segments WHERE imdb_id_int = ?", (imdb_id,))
        self._db_conn.execute("DELETE FROM movie_subtitles WHERE imdb_id_int = ?", (imdb_id,))
        self._db_conn.commit()
