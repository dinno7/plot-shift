from dataclasses import dataclass
from datetime import timedelta


@dataclass()
class NarrativeWindow:
    """
    This is different with subtitle segments and contain multiple segments as a window
    """

    index: int
    from_segment_idx: int
    to_segment_idx: int
    start: timedelta
    end: timedelta
    text: str
