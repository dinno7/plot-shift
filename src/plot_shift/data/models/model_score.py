from dataclasses import dataclass


@dataclass
class ModelScore:
    imdb_id_int: int
    from_segment_idx: int | None
    to_segment_idx: int | None
    window_idx: int
    total_windows: int
    scorer_name: str
    scorer_kind: str
    dimension: str
    score: float
