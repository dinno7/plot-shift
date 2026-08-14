import sqlite3
from datetime import datetime

from plot_shift.data import SubtitleMeta
from plot_shift.data.repositories.repo import SubtitleMetaRepository


class SubtitleMetaRepositorySqliteRepository(SubtitleMetaRepository):
    _INSERT_QUERY = """
        INSERT INTO downloaded_subtitles
        (imdb_id_int, file_id, file_name_on_disk, subtitle_id,
         download_count, new_download_count, language, upload_date, url, dump_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    _SELECT_ALL_QUERY = "SELECT * FROM downloaded_subtitles"

    def __init__(self, conn: sqlite3.Connection):
        self.db_conn = conn

    def insert_one(self, subtitle: SubtitleMeta) -> int | None:
        """Insert a downloaded subtitle. Returns the new row ID."""
        cursor = self.db_conn.cursor()
        try:
            cursor.execute(
                self._INSERT_QUERY,
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
            return last_id
        finally:
            cursor.close()

    def get_all(self) -> list[SubtitleMeta]:
        """Fetches all downloaded subtitles."""
        cursor = self.db_conn.execute(self._SELECT_ALL_QUERY)
        try:
            return [self._row_to_subtitle(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    @staticmethod
    def _row_to_subtitle(row: tuple) -> SubtitleMeta:
        """Convert a raw DB row to a DownloadedSubtitle dataclass."""
        return SubtitleMeta(
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
