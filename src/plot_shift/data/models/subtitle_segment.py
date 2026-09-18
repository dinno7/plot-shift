from dataclasses import dataclass
from datetime import timedelta


@dataclass
class SubtitleSegment:
    """A single scoreable, timestamped unit of cleaned subtitle text.

    One subtitle cue yields zero, one, or more segments (sentence-tokenized);
    every segment inherits the start/end of the cue it came from.
    """

    imdb_id_int: int
    segment_idx: int
    start: timedelta
    end: timedelta
    content: str
    id: int | None = None
