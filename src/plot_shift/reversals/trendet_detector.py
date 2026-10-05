"""Vendored, dependency-free port of trendet's identify_df_trends.

Source: alvarobartt/trendet v0.7, trendet/identification.py.
Only the core detection logic is ported; investpy, pandas and unidecode
dependencies are removed. Behavioural quirks of the original are preserved
on purpose so results stay comparable with Knight et al. (2024).
"""

from __future__ import annotations

from statistics import mean
from typing import Literal

from .base import ReversalDetector, TrendSegment

IdentifyMode = Literal["both", "up", "down"]


# ----------------------------------------------------------------------
# Core algorithm (exact port)
# ----------------------------------------------------------------------
def _running_mean_trends(values: list[float], window_size: int) -> list[tuple[int, int]]:
    """Detect trends on ``values`` with trendet's running-mean rule.

    Returns ``(from_idx, extremum_idx)`` pairs. For an *up* trend, pass the
    negated series (as the original does via ``np.negative``); the extremum
    is then the index of the running maximum.
    """
    limit: float | None = None
    vals: list[float] = []
    from_trend = 0
    trends: list[tuple[int, int]] = []

    for index, value in enumerate(values):
        if limit and limit > value:  # still inside the current trend
            vals.append(value)
            limit = mean(vals)
        elif limit and limit < value:  # trend broke against us
            if len(vals) > window_size:
                min_value = min(vals)
                counter = 0
                for counter, item in enumerate(vals):
                    if item == min_value:
                        break
                trends.append((from_trend, from_trend + counter))
            limit = None
            vals = []
        else:  # start a new run
            from_trend = index
            vals.append(value)
            limit = mean(vals)

    return trends


def _resolve_overlaps(
    ups: list[tuple[int, int]],
    downs: list[tuple[int, int]],
) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """Nested-trend removal, keeping the longer of each overlapping pair.

    NOTE: the flag-overwrite behaviour of the original loops is preserved
    verbatim (see module docstring quirks).
    """
    kept_up: list[tuple[int, int]] = []
    for u in ups:
        flag = True
        for d in downs:
            if d[0] < u[0] < d[1] or d[0] < u[1] < d[1]:
                flag = (u[1] - u[0]) > (d[1] - d[0])
            else:
                flag = True
        if flag:
            kept_up.append(u)

    kept_down: list[tuple[int, int]] = []
    for d in downs:
        flag = True
        for u in ups:
            if u[0] < d[0] < u[1] or u[0] < d[1] < u[1]:
                flag = (u[1] - u[0]) < (d[1] - d[0])
            else:
                flag = True
        if flag:
            kept_down.append(d)

    return kept_up, kept_down


# ----------------------------------------------------------------------
# Detector
# ----------------------------------------------------------------------
class TrendetDetector(ReversalDetector):
    """Drop-in replacement for trendet.identify_df_trends on raw score lists.

    Parameters match the original: ``window_size`` must be >= 3 and
    ``identify`` is one of ``'both' | 'up' | 'down'`` (not 'up_trends' —
    the original accepts only 'up'/'down').
    """

    def __init__(self, window_size: int = 5, identify: IdentifyMode = "both") -> None:
        if not isinstance(window_size, int) or window_size < 3:
            raise ValueError("window_size must be an int equal or higher than 3!")
        if identify not in ("both", "up", "down"):
            raise ValueError("identify must be one of ['both', 'up', 'down']!")
        self.window_size = window_size
        self.identify = identify

    @property
    def name(self) -> str:
        return "trendet"

    # ------------------------------------------------------------------
    def trends(self, scores: list[float]) -> list[TrendSegment]:
        scores = [float(s) for s in scores]
        if not scores:
            return []

        ups = _running_mean_trends([-s for s in scores], self.window_size)
        downs = _running_mean_trends(scores, self.window_size)

        if self.identify == "up":
            kept_up, kept_down = ups, []
        elif self.identify == "down":
            kept_up, kept_down = [], downs
        else:
            kept_up, kept_down = _resolve_overlaps(ups, downs)

        segments = [TrendSegment("up", s, e) for s, e in kept_up] + [
            TrendSegment("down", s, e) for s, e in kept_down
        ]
        segments.sort(key=lambda seg: (seg.start, seg.end))
        return segments
