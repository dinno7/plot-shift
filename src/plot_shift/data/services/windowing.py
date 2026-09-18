"""Fixed-count, real-time windowing for reversal detection (Knight et al.).

Knight's method needs the same number of windows for every movie regardless
of its length, so short and long movies stay comparable. We keep the window
*count* fixed and let window *width* vary with each movie's real duration.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean


@dataclass(frozen=True, slots=True)
class TimedScore:
    start_seconds: float
    end_seconds: float
    score: float


class FixedCountTimeWindower:
    """Splits a movie's runtime into ``n_windows`` equal-width windows and
    averages the scores of segments whose midpoint falls in each window."""

    def __init__(self, n_windows: int = 100) -> None:
        if n_windows < 1:
            raise ValueError("n_windows must be >= 1")
        self.n_windows = n_windows

    def window(self, timed_scores: list[TimedScore], total_duration_seconds: float) -> list[float]:
        if total_duration_seconds <= 0 or not timed_scores:
            return []

        width = total_duration_seconds / self.n_windows
        buckets: list[list[float]] = [[] for _ in range(self.n_windows)]
        for timed_score in timed_scores:
            midpoint = (timed_score.start_seconds + timed_score.end_seconds) / 2
            bucket_idx = min(int(midpoint // width), self.n_windows - 1)
            buckets[bucket_idx].append(timed_score.score)

        overall_mean = fmean(ts.score for ts in timed_scores)
        # empty windows fall back to the movie's overall mean
        # (a neutral no-op for trend detection) instead of interpolating
        # from neighboring windows; revisit if empty windows are common.
        return [fmean(bucket) if bucket else overall_mean for bucket in buckets]


def demo() -> None:
    windower = FixedCountTimeWindower(n_windows=4)
    # Each window is 10s wide (40s / 4); one segment centered in each window.
    scores = [
        TimedScore(4.0, 6.0, 1.0),
        TimedScore(14.0, 16.0, -1.0),
        TimedScore(24.0, 26.0, 1.0),
        TimedScore(34.0, 36.0, -1.0),
    ]
    result = windower.window(scores, total_duration_seconds=40.0)
    assert result == [1.0, -1.0, 1.0, -1.0], result
    assert windower.window([], 40.0) == []


if __name__ == "__main__":
    demo()
