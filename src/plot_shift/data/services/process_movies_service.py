import logging
from pathlib import Path

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.models.movie_subtitle_meta import MovieSubtitlesMeta
from plot_shift.data.repository import PlotShiftDB
from plot_shift.data.subtitle_parser_service import SubtitleParserService

logger = logging.getLogger(__name__)


class ProcessMoviesService:
    """Orchestrates parsing raw .srt files and persisting them to the DB."""

    def __init__(self, db: PlotShiftDB, subtitles_dir: str | Path) -> None:
        self._db = db
        self._subtitles_dir = Path(subtitles_dir)

    @staticmethod
    def is_valid_sub(total_words: int, duration_minutes: int) -> bool:
        return total_words >= 1000 and total_words >= (duration_minutes / 5)

    def process(self, batch_size: int = 500) -> dict[str, int]:
        """
        Parse all subtitle files referenced in subtitles_meta and insert into subtitles table.

        Returns:
            Dictionary with processing statistics.
        """
        stats = {"processed": 0, "inserted": 0, "skipped_missing": 0, "errors": 0}

        sub_metas = self._db.subtitle_meta.get_all()  # Raw downloaded subtitle's metadata
        logger.info("Found %d subtitle metadata records to process.", len(sub_metas))

        buffer: list[MovieSubtitlesMeta] = []
        for sub_meta in sub_metas:
            file_path = self._subtitles_dir / sub_meta.file_name_on_disk
            # Safety check: ensure file exists before attempting parse
            if not file_path.exists():
                logger.warning(
                    "Subtitle file missing on disk: %s (IMDB: %d)",
                    sub_meta.file_name_on_disk,
                    sub_meta.imdb_id_int,
                )
                stats["skipped_missing"] += 1
                continue
            try:
                sub_parser = SubtitleParserService(str(file_path))
                movie_parsed_sub = sub_parser.parse()

                if not movie_parsed_sub:
                    logger.warning("No valid cues parsed from %s", sub_meta.file_name_on_disk)
                    stats["errors"] += 1
                    continue

                buffer.append(movie_parsed_sub)
                stats["processed"] += 1

                # INFO: Batch insert to avoid memory bloat and improve DB throughput
                if len(buffer) >= batch_size:
                    self._db.movie_subtitles_meta.insert_many(buffer)
                    stats["inserted"] += len(buffer)
                    buffer.clear()
                    logger.debug("Inserted batch of %d cues.", batch_size)

            except Exception:
                logger.exception("Failed to parse %s", sub_meta.file_name_on_disk)
                stats["errors"] += 1

        # INFO: Drain remaining buffer
        if buffer:
            self._db.movie_subtitles_meta.insert_many(buffer)
            stats["inserted"] += len(buffer)
            buffer.clear()

        logger.info("Ingestion complete: %s", stats)
        return stats


# Example
if __name__ == "__main__":
    print("Initiating repository")
    repo = PlotShiftSqliteDB("data/proceeded/data.db")
    print("Initiating processor")
    processor = ProcessMoviesService(repo, "data/raw/subtitles")
    print("Starting process, Do not interrupt process")
    processor.process()
    print("Process end")
