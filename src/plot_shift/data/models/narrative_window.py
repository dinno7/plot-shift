from dataclasses import dataclass
from datetime import timedelta


@dataclass()
class NarrativeWindow:
    """
    This is different with subtitle segments and contain multiple segments as a window
    """

    index: int
    from_segment_idx: int | None  # It is possible some window do not cover any segment
    to_segment_idx: int | None
    start: timedelta
    end: timedelta
    text: str
