from dataclasses import dataclass


@dataclass
class SentenceModelScore:
    imdb_id_int: int
    sentence_idx: int
    model: str
    dimension: str
    score: float
