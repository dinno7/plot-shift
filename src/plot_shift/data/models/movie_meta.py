from dataclasses import dataclass


@dataclass
class MovieMeta:
    """Represents a single movies_meta cue with raw and cleaned text."""

    imdb_id: str
    average_rating: float
    num_votes: int
    title_type: str
    primary_title: str
    original_title: str
    start_year: int
    runtime_minutes: int
    id: int | None = None
    imdb_id_int: int | None = None
    genres: str | None = None
