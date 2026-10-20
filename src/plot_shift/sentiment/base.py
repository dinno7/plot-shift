"""Sentiment scorer protocol shared by all scoring approaches."""

from abc import ABC
from dataclasses import dataclass
from enum import Enum


class ScorerKind(Enum):
    LEXICON = "lexicon"
    TRANSFORMER = "transformer"
    API = "api"


@dataclass(frozen=True)
class SentimentScorer(ABC):
    """Any model that maps a unit of text to a continuous sentiment score."""

    def score(self, text: str) -> Score:
        """Return the continuous (unnormalized) score for ``text``."""
        raise NotImplementedError

    @property
    def scorer_name(self) -> str:
        """Return then name of scorer"""
        raise NotImplementedError

    @property
    def scorer_kind(self) -> ScorerKind:
        """Return the kind of scorer"""
        raise NotImplementedError


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
    def dimensions(self) -> list[DimensionScore]:
        return self._dimensions

    def __str__(self) -> str:
        buf = ""
        for dimension in self._dimensions:
            buf += f"{dimension.kind.value}: {dimension.value}, "
        return buf.rstrip(", ")


@dataclass(frozen=True, slots=True)
class DimensionScore:
    value: float
    kind: DimensionKind


class DimensionKind(Enum):
    VALENCE = "valence"
    AROUSAL = "arousal"
    DOMINANCE = "dominance"
