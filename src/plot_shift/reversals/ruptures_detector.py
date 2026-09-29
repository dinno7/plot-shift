"""Reversal detector backed by ``ruptures`` change-point detection."""

from __future__ import annotations

import numpy as np
import ruptures as rpt

from plot_shift.reversals.base import Direction, ReversalDetector, TrendSegment


class RupturesReversalDetector(ReversalDetector):
    """PELT change-points → up/down segments → Knight-style reversal stats.

    ``min_size`` is the closest analogue to trendet's ``window_size`` (shortest
    accepted segment). ``penalty`` controls how many change-points PELT keeps.
    """

    def __init__(self, min_size: int = 5, penalty: float = 1.0) -> None:
        if min_size < 2:
            raise ValueError("min_size must be >= 2")
        if penalty <= 0:
            raise ValueError("penalty must be > 0")
        self.min_size = min_size
        self.penalty = penalty

    @property
    def name(self) -> str:
        return "ruptures"

    def trends(self, scores: list[float]) -> list[TrendSegment]:
        if len(scores) < self.min_size * 2:
            return []

        signal = np.asarray(scores, dtype=np.float64).reshape(-1, 1)
        algo = rpt.Pelt(model="l2", min_size=self.min_size).fit(signal)
        # predict returns end indices of segments, last == n
        breakpoints = algo.predict(pen=self.penalty)
        return _segments_from_breakpoints(scores, breakpoints)


def _segments_from_breakpoints(scores: list[float], breakpoints: list[int]) -> list[TrendSegment]:
    """Label each PELT piece by slope sign (end − start of the piece)."""
    trends: list[TrendSegment] = []
    start = 0
    for end_exclusive in breakpoints:
        end = end_exclusive - 1
        if end < start:
            continue
        slope = scores[end] - scores[start]
        if slope == 0.0:
            start = end_exclusive
            continue
        direction: Direction = "up" if slope > 0.0 else "down"
        trends.append(TrendSegment(direction, start, end))
        start = end_exclusive
    return trends
