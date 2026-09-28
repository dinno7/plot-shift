from __future__ import annotations

import sqlite3
from types import TracebackType
from typing import Self

from plot_shift.data.repositories import (
    ModelScoreSqliteRepository,
    MovieMetaSqliteRepository,
    MovieSubtitlesSqliteRepository,
    ReversalFeaturesSqliteRepository,
    SubtitleMetaRepositorySqliteRepository,
    SubtitleSegmentsSqliteRepository,
)
from plot_shift.data.repository import (
    ModelScoresRepository,
    MovieMetaRepository,
    MovieSubtitlesRepository,
    ReversalFeaturesRepository,
    SubtitleMetaRepository,
    SubtitleSegmentsRepository,
)


class PlotShiftSqliteDB:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def __enter__(self) -> Self:
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self.conn:
            self.conn.close()

    def _require_conn(self) -> sqlite3.Connection:
        if self.conn is None:
            raise RuntimeError("PlotShiftSqliteDB must be used as a context manager")
        return self.conn

    @property
    def movies_meta(self) -> MovieMetaRepository:
        return MovieMetaSqliteRepository(self._require_conn())

    @property
    def subtitle_meta(self) -> SubtitleMetaRepository:
        return SubtitleMetaRepositorySqliteRepository(self._require_conn())

    @property
    def movie_subtitles(self) -> MovieSubtitlesRepository:
        return MovieSubtitlesSqliteRepository(self._require_conn())

    @property
    def subtitle_segments(self) -> SubtitleSegmentsRepository:
        return SubtitleSegmentsSqliteRepository(self._require_conn())

    @property
    def model_scores(self) -> ModelScoresRepository:
        return ModelScoreSqliteRepository(self._require_conn())

    @property
    def reversal_features(self) -> ReversalFeaturesRepository:
        return ReversalFeaturesSqliteRepository(self._require_conn())
