from __future__ import annotations

from plot_shift.reversals.base import ReversalDetector, ReversalStats, TrendSegment
from plot_shift.reversals.ruptures_detector import RupturesReversalDetector
from plot_shift.reversals.trendet_detector import TrendetDetector

__all__ = [
    "ReversalDetector",
    "ReversalStats",
    "RupturesReversalDetector",
    "TrendSegment",
    "TrendetDetector",
    "create_reversal_detector",
]


def create_reversal_detector(
    name: str,
    *,
    window_size: int = 5,
    ruptures_penalty: float = 1.0,
) -> ReversalDetector:
    """Build a detector by name (``ruptures``)."""
    key = name.strip().lower()
    if key == "ruptures":
        return RupturesReversalDetector(min_size=window_size, penalty=ruptures_penalty)
    elif key == "trendet":
        return TrendetDetector(window_size=window_size)
    raise ValueError(f"unknown reversal detector: {name!r} (expected ruptures)")
