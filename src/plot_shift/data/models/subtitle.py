import re
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class Subtitle:
    """Represents a single subtitle cue with raw and cleaned text."""

    index: int
    imdb_id_int: int
    start: timedelta
    end: timedelta
    text_raw: str
    text: str = field(init=False)
    id: int | None

    def __post_init__(self):
        self.text = self._clean(self.text_raw)

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    @staticmethod
    def _clean(raw: str) -> str:
        """Remove common SRT artifacts from subtitle text."""
        cleaned = raw
        # Remove HTML-like tags (<i>, <b>, <font color="...">, etc.)
        cleaned = re.sub(r"<[^>]+>", "", cleaned)
        # Remove ASS/SSA override tags ({\an8}, {\c&H00FFFF&}, etc.)
        cleaned = re.sub(r"\{[^}]*\}", "", cleaned)
        # Remove hearing-impaired descriptors in brackets [LAUGHTER], (SIGHING)
        cleaned = re.sub(r"[\[(][^)\]]*[\])]", "", cleaned)
        # Collapse multiple spaces/newlines into single space
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n\s*\n", "\n", cleaned)
        return cleaned.strip()

    def __str__(self):
        return f"[{self.start} --> {self.end}] {self.text}"
