import re
from datetime import timedelta
from pathlib import Path

from plot_shift.data import Subtitle


class SrtParser:
    """Simple OOP parser for .srt subtitle files."""

    TIME_PATTERN: re.Pattern[str] = re.compile(
        r"(\d{2}:\d{2}:\d{2}[.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[.,]\d{3})"
    )

    def __init__(self, filepath: str):
        self.filepath: str = filepath
        self.subtitles: list[Subtitle] = []
        first_part_of_file_name = Path(filepath).name.split("_")[0]
        self.imdb_id_int: int = int(first_part_of_file_name)

    def parse(self) -> list[Subtitle]:
        """Parse the file and populate self.subtitles."""
        with open(self.filepath, "r", encoding="utf-8-sig") as f:
            content = f.read()

        blocks = re.split(r"\n\s*\n", content.strip())
        self.subtitles = []

        for block in blocks:
            entry = self._parse_block(block)
            if entry is not None:
                self.subtitles.append(entry)

        return self.subtitles

    def _parse_block(self, block: str) -> Subtitle | None:
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

        return Subtitle(
            index=int(lines[0]),
            imdb_id_int=self.imdb_id_int,
            start=self._to_timedelta(time_match.group(1)),
            end=self._to_timedelta(time_match.group(2)),
            text_raw=raw_text,
            id=None,
        )

    @staticmethod
    def _to_timedelta(time_str: str) -> timedelta:
        """Convert SRT timestamp string to timedelta."""
        normalized = time_str.replace(",", ".")
        h, m, s = normalized.split(":")
        seconds, ms = s.split(".")
        return timedelta(hours=int(h), minutes=int(m), seconds=int(seconds), milliseconds=int(ms))


# # --- Usage Example ---
# if __name__ == "__main__":
#     parser = SrtParser("./34583_186233.srt")
#     subs = parser.parse()
#
#     for sub in subs[:5]:
#         print(f"CLEAN: {sub.index}")
#         print(f"CLEAN: {sub.imdb_id_int}")
#         print(f"CLEAN: {sub.text}")
#         print(f"RAW:   {sub.text_raw}")
#         print(f"TIME:  {sub.start} --> {sub.end} ({sub.duration})")
#         print()
