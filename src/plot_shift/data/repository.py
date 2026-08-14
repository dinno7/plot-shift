import sqlite3

from plot_shift.data import (
    MovieMetaSqliteRepository,
    PlotShiftDB,
    SubtitleMetaRepositorySqliteRepository,
)


class PlotShiftSqliteDB(PlotShiftDB):
    def __init__(self, dbpath: str):
        self.db_conn = sqlite3.connect(dbpath)
        self.movies_meta = MovieMetaSqliteRepository(self.db_conn)
        self.subtitle_meta = SubtitleMetaRepositorySqliteRepository(self.db_conn)
        self.subtitles = SubtitleMetaRepositorySqliteRepository(self.db_conn)

    def close(self) -> None:
        self.db_conn.close()
