"""Reversal detection: turn a windowed score series into reversal stats."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import pairwise
from statistics import fmean
from typing import Literal

Direction = Literal["up", "down"]


@dataclass(frozen=True, slots=True)
class TrendSegment:
    direction: Direction
    start: int  # inclusive
    end: int  # inclusive


@dataclass(frozen=True, slots=True)
class ReversalStats:
    n_reversals: int
    mean_intensity: float
    max_intensity: float
    series_length: int


class ReversalDetector(ABC):
    """Detect narrative reversals on a fixed-length windowed score series."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Stable detector name (e.g. ``ruptures``)."""

    @abstractmethod
    def detect(self, scores: list[float]) -> ReversalStats:
        """Return reversal count and peak-to-trough intensities for ``scores``."""


def stats_from_trends(scores: list[float], trends: list[TrendSegment]) -> ReversalStats:
    """Knight-style stats: Up↔Down flips and |peak−trough| between extrema."""
    series_length = len(scores)
    if len(trends) < 2:
        return ReversalStats(0, 0.0, 0.0, series_length)

    intensities: list[float] = []
    for prev, nxt in pairwise(trends):
        if prev.direction == nxt.direction:
            continue
        intensities.append(abs(_extremum(scores, prev) - _extremum(scores, nxt)))

    if not intensities:
        return ReversalStats(0, 0.0, 0.0, series_length)

    return ReversalStats(
        n_reversals=len(intensities),
        mean_intensity=float(fmean(intensities)),
        max_intensity=float(max(intensities)),
        series_length=series_length,
    )


def _extremum(scores: list[float], trend: TrendSegment) -> float:
    segment = scores[trend.start : trend.end + 1]
    if trend.direction == "up":
        return max(segment)
    return min(segment)
