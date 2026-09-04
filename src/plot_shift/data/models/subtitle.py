from dataclasses import dataclass
from datetime import timedelta


@dataclass
class Subtitle:
    """Represents a single subtitle cue with raw and cleaned text."""

    index: int
    imdb_id_int: int
    start: timedelta
    end: timedelta
    text_raw: str
    id: int | None

    @property
    def duration(self) -> timedelta:
        return self.end - self.start

    def __str__(self) -> str:
        return f"[{self.start} --> {self.end}] {self.text_raw}"
