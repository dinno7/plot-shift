"""Sentiment scorer protocol shared by all scoring approaches."""

from dataclasses import dataclass
from typing import Protocol


@dataclass()
class Score:
    """A continuous sentiment score for one unit of text (a cue or sentence).

    ``dimension`` is ``None`` for single-valued scorers (VADER compound, the
    semantic model) and one of ``valence``/``arousal``/``dominance`` for the
    multi-dimensional VAD scorer.
    """

    _dimensions: list[DimensionScore]

    def __init__(self) -> None:
        self._dimensions = []

    def add_dimension_score(self, dimension: DimensionScore) -> None:
        self._dimensions.append(dimension)

    @property
    def dimension_count(self) -> int:
        return len(self._dimensions)

    @property
    def dimensions_avg(self) -> float:
        return sum([d.value for d in self._dimensions]) / self.dimension_count

    @property
    def dimention(self) -> list[DimensionScore]:
        return self._dimensions


@dataclass(frozen=True, slots=True)
class DimensionScore:
    value: float
    name: str | None = None


class SentimentScorer(Protocol):
    """Any model that maps a unit of text to a continuous sentiment score."""

    model_name: str
    """Identifier used as the ``model`` column in the score series / features."""

    def score(self, text: str) -> Score:
        """Return the (single) continuous score for ``text`` in [-1, 1]."""
        ...
