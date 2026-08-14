from __future__ import annotations

import logging
from pathlib import Path

from plot_shift.data.models import Subtitle
from plot_shift.data.parser import SrtParser
from plot_shift.data.repository import PlotShiftDB

logger = logging.getLogger(__name__)


class SubtitleIngestionService:
    """Orchestrates parsing raw .srt files and persisting them to the DB."""

    def __init__(self, db: PlotShiftDB, subtitles_dir: str | Path) -> None:
        self._db = db
        self._subtitles_dir = Path(subtitles_dir)

    def ingest_all(self, batch_size: int = 500) -> dict[str, int]:
        """
        Parse all subtitle files referenced in subtitles_meta and insert into subtitles table.

        Returns:
            Dictionary with processing statistics.
        """
        stats = {"processed": 0, "inserted": 0, "skipped_missing": 0, "errors": 0}

        metas = self._db.subtitle_meta.get_all()
        logger.info("Found %d subtitle metadata records to process.", len(metas))

        buffer: list[Subtitle] = []

        for meta in metas:
            file_path = self._subtitles_dir / meta.file_name_on_disk

            # Safety check: ensure file exists before attempting parse
            if not file_path.exists():
                logger.warning(
                    "Subtitle file missing on disk: %s (IMDB: %d)",
                    meta.file_name_on_disk,
                    meta.imdb_id_int,
                )
                stats["skipped_missing"] += 1
                continue

            try:
                parser = SrtParser(str(file_path))
                parsed_subs = parser.parse()

                if not parsed_subs:
                    logger.warning("No valid cues parsed from %s", meta.file_name_on_disk)
                    stats["errors"] += 1
                    continue

                buffer.extend(parsed_subs)
                stats["processed"] += 1

                # Batch insert to avoid memory bloat and improve DB throughput
                if len(buffer) >= batch_size:
                    self._db.subtitles.insert_many(buffer)
                    stats["inserted"] += len(buffer)
                    buffer.clear()
                    logger.debug("Inserted batch of %d cues.", batch_size)

            except Exception as e:
                logger.error("Failed to parse %s: %s", meta.file_name_on_disk, e, exc_info=True)
                stats["errors"] += 1

        # Flush remaining buffer
        if buffer:
            self._db.subtitles.insert_many(buffer)
            stats["inserted"] += len(buffer)
            buffer.clear()

        logger.info("Ingestion complete: %s", stats)
        return stats


# Example
# if __name__ == "__main__":
#     repo = PlotShiftSqliteDB("data/proceeded/data.db")
#     ingestion = SubtitleIngestionService(repo, "data/raw/subtitles")
#     ingestion.ingest_all()
