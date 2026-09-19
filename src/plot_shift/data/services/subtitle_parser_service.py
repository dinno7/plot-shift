import re
from datetime import timedelta
from pathlib import Path

from plot_shift.data import Subtitle
from plot_shift.data.models.movie_subtitle_meta import MovieSubtitle
from plot_shift.data.models.subtitle_segment import SubtitleSegment
from plot_shift.data.services.movie_subtitles_service import MovieSubtitlesService


class SubtitleParserService:
    """Simple OOP parser for .srt subtitle files."""

    TIME_PATTERN: re.Pattern[str] = re.compile(
        r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})"
    )

    def __init__(self, filepath: str):
        self.filepath: str = filepath
        first_part_of_file_name = Path(filepath).name.split("_")[0]
        self.imdb_id_int: int = int(first_part_of_file_name)

        self.subtitles: list[Subtitle] = []
        self.movie_subtitle_service: MovieSubtitlesService = MovieSubtitlesService(self.imdb_id_int)

    def parse(self) -> MovieSubtitle:
        """Parse the file and populate self.subtitles."""
        with open(self.filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()

            blocks = re.split(r"\n\s*\n", content.strip())

            for block in blocks:
                entry = self._parse_block(block)
                if entry is not None:
                    self.movie_subtitle_service.add(entry)

            return self.movie_subtitle_service.process()

    def _parse_block(self, block: str) -> SubtitleSegment | None:
        """Parse a single subtitle block, returning None if malformed."""
        lines = block.strip().splitlines()
        if len(lines) < 2:
            return None

        if not lines[0].strip().isdigit():
            return None

        time_match = self.TIME_PATTERN.search(lines[1])
        if not time_match:
            return None

        raw_text = "\n".join(lines[2:]).strip()

        return SubtitleSegment(
            segment_idx=int(lines[0]),
            imdb_id_int=self.imdb_id_int,
            start=self._to_timedelta(time_match.group(1)),
            end=self._to_timedelta(time_match.group(2)),
            content=raw_text,
            id=None,
        )

    @staticmethod
    def _to_timedelta(time_str: str) -> timedelta:
        """Convert SRT timestamp string to timedelta."""
        normalized = time_str.replace(",", ".")
        h, m, s = normalized.split(":")
        seconds, ms = s.split(".")
        return timedelta(hours=int(h), minutes=int(m), seconds=int(seconds), milliseconds=int(ms))


# --- Usage Example ---
if __name__ == "__main__":
    parser = SubtitleParserService("./34583_186233.srt")
    subs = parser.parse()
    print(subs._segments)
