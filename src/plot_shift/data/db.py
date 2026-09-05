import sqlite3

from plot_shift.data.repositories import (
    MovieMetaSqliteRepository,
    SentenceModelScoreSqliteRepository,
    SubtitleMetaRepositorySqliteRepository,
    SubtitleSqliteRepository,
)
from plot_shift.data.repositories.sqlite.movie_subtitles_meta import (
    MovieSubtitlesMetaSqliteRepository,
)
from plot_shift.data.repository import PlotShiftDB


class PlotShiftSqliteDB(PlotShiftDB):
    def __init__(self, dbpath: str):
        self.db_conn = sqlite3.connect(dbpath)
        self.movies_meta = MovieMetaSqliteRepository(self.db_conn)
        self.subtitle_meta = SubtitleMetaRepositorySqliteRepository(self.db_conn)
        self.subtitles = SubtitleSqliteRepository(self.db_conn)
        self.movie_subtitles_meta = MovieSubtitlesMetaSqliteRepository(dbpath)
        self.sentence_model_scores = SentenceModelScoreSqliteRepository(dbpath)

    def close(self) -> None:
        self.db_conn.close()
