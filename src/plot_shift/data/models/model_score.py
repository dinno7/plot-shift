from dataclasses import dataclass


@dataclass
class ModelScore:
    imdb_id_int: int
    from_segment_idx: int
    to_segment_idx: int
    window_idx: int
    total_windows: int
    model: str
    dimension: str
    score: float
