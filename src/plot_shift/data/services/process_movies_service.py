import logging
from pathlib import Path

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.models.movie_subtitle_meta import MovieSubtitle
from plot_shift.data.services.subtitle_parser_service import SubtitleParserService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
logger.addHandler(handler)


class ProcessMoviesService:
    """Orchestrates parsing raw .srt files and persisting them to the DB."""

    def __init__(self, db: PlotShiftSqliteDB, subtitles_dir: str | Path) -> None:
        self._db = db
        self._subtitles_dir = Path(subtitles_dir)

    @staticmethod
    def is_valid_sub(total_words: int, duration_minutes: int) -> bool:
        return total_words >= 1000 and total_words >= (duration_minutes / 5)

    def process(self, batch_size: int = 100) -> dict[str, int]:
        """
        Parse all subtitle files referenced in subtitles_meta and insert into subtitles table.

        Returns:
            Dictionary with processing statistics.
        """
        stats = {"processed": 0, "inserted": 0, "skipped_missing": 0, "errors": 0}

        sub_metas = self._db.subtitle_meta.get_all()  # Raw downloaded subtitle's metadata
        logger.info("Found %d subtitle metadata records to process.", len(sub_metas))

        logger.info("Try to batch upsert movies with bach size of %d", batch_size)
        buffer: list[MovieSubtitle] = []
        for indx, sub_meta in enumerate(sub_metas):
            logger.info(
                "Parsing %s (%d/%d)",
                sub_meta.file_name_on_disk,
                indx + 1,
                len(sub_metas),
            )
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
                    logger.warning("No valid segments parsed from %s", sub_meta.file_name_on_disk)
                    stats["errors"] += 1
                    continue

                buffer.append(movie_parsed_sub)
                stats["processed"] += 1

                # INFO: Batch insert to avoid memory bloat and improve DB throughput
                if len(buffer) >= batch_size:
                    logger.info("Inserting batch of %d segments.", batch_size)
                    self._db.movie_subtitles.upsert_many(buffer)
                    stats["inserted"] += len(buffer)
                    buffer.clear()
                    logger.info("Batch of %d segments inserted.", batch_size)

            except Exception:
                logger.exception("Failed to parse %s", sub_meta.file_name_on_disk)
                stats["errors"] += 1

        # INFO: Drain remaining buffer
        if buffer:
            logger.info("Draining buffer")
            self._db.movie_subtitles.upsert_many(buffer)
            stats["inserted"] += len(buffer)
            buffer.clear()
            logger.info("Inserted batch of %d segments.", batch_size)

        return stats


def run_process(
    db_path: str = "data/proceeded/data.db",
    subtitles_dir: str = "data/raw/subtitles",
    batch_size: int = 100,
) -> dict[str, int]:
    with PlotShiftSqliteDB(db_path) as repo:
        processor = ProcessMoviesService(repo, subtitles_dir)
        print("Start process, please do not interrupt, when process done you will see done message")
        result = processor.process(batch_size=batch_size)
        print("Process done")
        return result


if __name__ == "__main__":
    print(run_process())
