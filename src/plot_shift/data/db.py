import sqlite3

from plot_shift.data.repositories import (
    MovieMetaSqliteRepository,
    MovieSubtitlesSqliteRepository,
    SentenceModelScoreSqliteRepository,
    SubtitleMetaRepositorySqliteRepository,
    SubtitleSegmentsSqliteRepository,
)
from plot_shift.data.repository import (
    MovieMetaRepository,
    MovieSubtitlesRepository,
    SentenceModelScoreRepository,
    SubtitleMetaRepository,
)


class PlotShiftSqliteDB:
    def __init__(self, db_path):
        self.db_path = db_path

    def __enter__(self):
        self.conn = sqlite3.connect(self.db_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()

    @property
    def movies_meta(self) -> MovieMetaRepository:
        return MovieMetaSqliteRepository(self.conn)

    @property
    def subtitle_meta(self) -> SubtitleMetaRepository:
        return SubtitleMetaRepositorySqliteRepository(self.conn)

    @property
    def movie_subtitles(self) -> MovieSubtitlesRepository:
        return MovieSubtitlesSqliteRepository(self.conn)

    @property
    def subtitle_segments(self):
        return SubtitleSegmentsSqliteRepository(self.conn)

    @property
    def sentence_model_scores(self) -> SentenceModelScoreRepository:
        return SentenceModelScoreSqliteRepository(self.db_path)
