# """Reversal detector backed by ``ruptures`` change-point detection."""
#
# from __future__ import annotations
#
# import math
#
# import numpy as np
# import ruptures as rpt
#
# from plot_shift.reversals.base import Direction, ReversalDetector, TrendSegment
#
#
# class RupturesReversalDetector(ReversalDetector):
#     """PELT piecewise-linear fit → up/down trends → Knight-style reversal stats.
#
#     The series is fitted with continuous straight-line pieces (``clinear`` cost);
#     each piece is a trend whose direction is the sign of its fitted slope, and
#     consecutive pieces with the same direction are merged into one trend.
#
#     ``min_size`` is the shortest accepted piece in windows, the analogue of
#     trendet's ``window_size``. ``penalty`` is scale-free: PELT receives
#     ``penalty * var(series) * log(n)`` (BIC-style), so the same value means the
#     same sensitivity for every scorer regardless of its score range.
#     """
#
#     def __init__(self, min_size: int = 5, penalty: float = 1.0) -> None:
#         if min_size < 2:
#             raise ValueError("min_size must be >= 2")
#         if penalty <= 0:
#             raise ValueError("penalty must be > 0")
#         self.min_size = min_size
#         self.penalty = penalty
#
#     @property
#     def name(self) -> str:
#         return "ruptures"
#
#     def trends(self, scores: list[float]) -> list[TrendSegment]:
#         signal = np.asarray(scores, dtype=np.float64)
#         variance = float(signal.var()) if len(signal) else 0.0
#         if len(signal) < self.min_size * 2 or variance == 0.0:
#             return []
#
#         algo = rpt.Pelt(model="clinear", min_size=self.min_size, jump=1).fit(signal.reshape(-1, 1))
#         # predict returns end indices of segments, last == n
#         breakpoints = algo.predict(pen=self.penalty * variance * math.log(len(signal)))
#         return _segments_from_breakpoints(signal, breakpoints)
#
#
# def _segments_from_breakpoints(signal: np.ndarray, breakpoints: list[int]) -> list[TrendSegment]:
#     """Label each piece by its least-squares slope and merge same-direction neighbours.
#
#     ``clinear`` pieces are continuous, so each piece starts at the previous
#     piece's last point; that shared point is the turning point of a reversal.
#     """
#     trends: list[TrendSegment] = []
#     start = 0
#     for end_exclusive in breakpoints:
#         start = max(start - 1, 0)
#         piece = signal[start:end_exclusive]
#         slope = np.polyfit(np.arange(len(piece)), piece, 1)[0] if len(piece) > 1 else 0.0
#         if slope != 0.0:
#             direction: Direction = "up" if slope > 0.0 else "down"
#             if trends and trends[-1].direction == direction:
#                 trends[-1] = TrendSegment(direction, trends[-1].start, end_exclusive - 1)
#             else:
#                 trends.append(TrendSegment(direction, start, end_exclusive - 1))
#         start = end_exclusive
#     return trends
"""Ruptures-based reversal detector."""

from __future__ import annotations

import numpy as np
import ruptures as rpt

from .base import Direction, ReversalDetector, TrendSegment  # نام ماژول پایه‌ات


class RupturesReversalDetector(ReversalDetector):
    """Detect reversals with the ``ruptures`` change-point library (PELT).

    Unlike ``trendet`` (which tracks a running mean), ruptures finds
    statistically optimal segment boundaries. Direction of each segment is
    inferred from the sign of its local trend, and adjacent same-direction
    segments are merged so the output matches the up/down alternation that
    ``stats_from_trends`` expects.
    """

    # self, min_size: int = 5, penalty: float = 1.0,
    def __init__(
        self,
        model: str = "l2",
        penalty: float | None = None,
        min_size: int = 3,
        jump: int = 1,
        smooth: int = 3,
    ) -> None:
        """
        Args:
            model:   ruptures cost model. "l2" = mean shifts (best for valence),
                     "rvar" = variance shifts, "rbf" = generic distribution shift.
            pen:     PELT penalty. If None, a BIC-style penalty
                     ``2 * var(y) * log(n)`` is used.
            min_size: minimum segment length (in windows). Prevents noise-
                      driven micro-reversals.
            jump:    subsampling step for speed; keep 1 for n=100.
            smooth:  moving-average window applied before detection (1 = off).
                     trendet is inherently smoothed; this replicates that.
        """
        self.model = model
        self.pen = penalty
        self.min_size = min_size
        self.jump = jump
        self.smooth = smooth

    @property
    def name(self) -> str:
        return "ruptures"

    # ------------------------------------------------------------------
    def trends(self, scores: list[float]) -> list[TrendSegment]:
        y = np.asarray(scores, dtype=float)
        n = len(y)
        if n < max(2 * self.min_size, 4):
            # not enough data for even one credible break
            direction = "up" if y[-1] >= y[0] else "down"
            return [TrendSegment(direction, 0, n - 1)]

        y = self._smooth(y)

        algo = rpt.Pelt(model=self.model, min_size=self.min_size, jump=self.jump).fit(y)

        pen = self.pen
        if pen is None:
            pen = 2.0 * float(np.var(y)) * float(np.log(n))

        bkps = algo.predict(pen=pen)  # e.g. [23, 58, 100]
        bounds = [0] + bkps  # segment ends are inclusive-1

        segments: list[TrendSegment] = []
        for start, stop in zip(bounds, bounds[1:]):
            end = stop - 1  # ruptures uses exclusive end
            segments.append(TrendSegment(self._direction(y, start, end), start, end))

        return self._merge_same_direction(segments)

    # ------------------------------------------------------------------
    # @staticmethod
    def _smooth(self, y: np.ndarray) -> np.ndarray:
        if self.smooth <= 1 or len(y) < self.smooth:
            return y
        kernel = np.ones(self.smooth) / self.smooth
        return np.convolve(y, kernel, mode="same")
        # k = max(1, int(getattr(RupturesReversalDetector, "_smooth", 1)))
        # return y

    def _direction(self, y: np.ndarray, start: int, end: int) -> Direction:
        """Sign of the segment's local trend (first-half mean vs second-half)."""
        seg = y[start : end + 1]
        half = max(1, len(seg) // 2)
        diff = float(np.mean(seg[-half:]) - np.mean(seg[:half]))
        return "up" if diff >= 0 else "down"

    @staticmethod
    def _merge_same_direction(
        segments: list[TrendSegment],
    ) -> list[TrendSegment]:
        merged: list[TrendSegment] = []
        for seg in segments:
            if merged and merged[-1].direction == seg.direction:
                last = merged[-1]
                merged[-1] = TrendSegment(last.direction, last.start, seg.end)
            else:
                merged.append(seg)
        return merged
