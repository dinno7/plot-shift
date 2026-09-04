from __future__ import annotations

import sqlite3
from datetime import timedelta

from plot_shift.data.models.movie_subtitle_meta import MovieSubtitlesMeta
from plot_shift.data.repository import MovieSubtitlesMetaRepository
from plot_shift.data.utils import stop_words, tokenize_all_words


class MovieSubtitlesMetaSqliteRepository(MovieSubtitlesMetaRepository):
    """
    Repository for persisting and retrieving MovieSubtitlesMeta.

    Note: This repository stores the PROCESSED state of the meta.
    Raw subtitle text is not stored in these tables; only cleaned
    sentences and aggregate statistics are persisted.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @staticmethod
    def _validate_processed(meta: MovieSubtitlesMeta) -> None:
        if not hasattr(meta, "sentences") or meta.sentences is None:
            raise ValueError(
                f"MovieSubtitlesMeta(imdb_id={meta.imdb_id}) must be processed "
                "before saving. Call meta.process() first."
            )

    @staticmethod
    def _prepare_meta_row(meta: MovieSubtitlesMeta) -> tuple[int, int, int, int, bool]:
        duration_minutes = int(meta.duration.total_seconds() // 60)
        return (
            meta.imdb_id,
            meta.words_count,
            meta.sentences_count,
            duration_minutes,
            meta.is_valid,
        )

    @staticmethod
    def _prepare_sentence_rows(meta: MovieSubtitlesMeta) -> list[tuple[int, str]]:
        return [(meta.imdb_id, sentence) for sentence in meta.sentences]

    def insert(self, meta: MovieSubtitlesMeta) -> None:
        """
        Persists processed MovieSubtitlesMeta and its sentences.

        IMPORTANT: Call meta.process() before saving to ensure
        _words and _sentences are populated.
        """
        if not hasattr(meta, "sentences") or meta.sentences is None:
            raise ValueError(
                "MovieSubtitlesMeta must be processed before saving. Call meta.process() first."
            )

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Upsert meta record
            cursor.execute(
                """
                INSERT INTO movie_subtitles_meta
                    (imdb_id_int, words_count, sentences_count, duration_minutes, is_valid)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(imdb_id_int) DO UPDATE SET
                    words_count = excluded.words_count,
                    sentences_count = excluded.sentences_count,
                    duration_minutes = excluded.duration_minutes,
                    is_valid = excluded.is_valid
            """,
                self._prepare_meta_row(meta),
            )

            # Replace all sentences for this imdb_id
            cursor.execute(
                "DELETE FROM movie_subtitles_sentences WHERE imdb_id_int = ?", (meta.imdb_id,)
            )

            sentences_data = [(meta.imdb_id, sentence) for sentence in meta.sentences]

            if sentences_data:
                cursor.executemany(
                    """INSERT INTO movie_subtitles_sentences
                            (imdb_id_int, content) VALUES (?, ?)
                        ON CONFLICT(imdb_id_int, content) DO NOTHING""",
                    sentences_data,
                )

            conn.commit()

    def insert_many(self, metas: list[MovieSubtitlesMeta]) -> None:
        if not metas:
            return

        # Validate ALL records before opening a transaction
        for meta in metas:
            self._validate_processed(meta)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Batch upsert meta records
            meta_rows = [self._prepare_meta_row(m) for m in metas]
            cursor.executemany(
                """
                INSERT INTO movie_subtitles_meta
                    (imdb_id_int, words_count, sentences_count, duration_minutes, is_valid)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(imdb_id_int) DO UPDATE SET
                    words_count = excluded.words_count,
                    sentences_count = excluded.sentences_count,
                    duration_minutes = excluded.duration_minutes,
                    is_valid = excluded.is_valid
            """,
                meta_rows,
            )

            # Batch delete old sentences for all affected imdb_ids
            imdb_ids = [m.imdb_id for m in metas]
            placeholders = ",".join("?" * len(imdb_ids))
            cursor.execute(
                f"DELETE FROM movie_subtitles_sentences WHERE imdb_id_int IN ({placeholders})",
                imdb_ids,
            )

            # Batch insert all new sentences in one executemany call
            all_sentences = []
            for meta in metas:
                all_sentences.extend(self._prepare_sentence_rows(meta))

            if all_sentences:
                cursor.executemany(
                    """INSERT INTO movie_subtitles_sentences 
                            (imdb_id_int, content) VALUES (?, ?)
                        ON CONFLICT(imdb_id_int, content) DO NOTHING
                    """,
                    all_sentences,
                )

            conn.commit()

    def find_by_imdb_id(self, imdb_id: int) -> MovieSubtitlesMeta | None:
        """
        Reconstructs a MovieSubtitlesMeta from the database.

        NOTE: The returned object has pre-computed statistics and cleaned
        sentences. The raw 'text' field will be empty since it is not
        stored in these tables. If you need to re-process, fetch raw
        subtitles separately and rebuild.
        """
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM movie_subtitles_meta WHERE imdb_id_int = ?", (imdb_id,)
            ).fetchone()

            if row is None:
                return None

            # Fetch associated sentences
            sentence_rows = conn.execute(
                "SELECT content FROM movie_subtitles_sentences WHERE imdb_id_int = ? ORDER BY id",
                (imdb_id,),
            ).fetchall()

            sentences = [r["content"] for r in sentence_rows]
            all_words: list[str] = []
            words: list[str] = []
            for sentence in sentences:
                tokens = tokenize_all_words(sentence)
                all_words.extend(tokens)
                words.extend(w for w in tokens if w not in stop_words)
            return MovieSubtitlesMeta(
                imdb_id=row["imdb_id_int"],
                words=words,
                sentences=sentences,
                duration=timedelta(minutes=row["duration_minutes"]),
                all_words=all_words,
            )

    def list_valid_imdb_ids(self) -> list[int]:
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT imdb_id_int FROM movie_subtitles_meta
                WHERE is_valid = 1
                ORDER BY imdb_id_int
                """
            ).fetchall()
            return [int(r["imdb_id_int"]) for r in rows]

    def exists(self, imdb_id: int) -> bool:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM movie_subtitles_meta WHERE imdb_id_int = ?", (imdb_id,)
            ).fetchone()
            return row is not None

    def delete(self, imdb_id: int) -> None:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM movie_subtitles_sentences WHERE imdb_id_int = ?", (imdb_id,))
            conn.execute("DELETE FROM movie_subtitles_meta WHERE imdb_id_int = ?", (imdb_id,))
            conn.commit()
