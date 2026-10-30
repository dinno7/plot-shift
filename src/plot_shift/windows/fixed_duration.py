from datetime import timedelta

from plot_shift.data.models import MovieSubtitle, NarrativeWindow, SubtitleSegment
from plot_shift.windows.base import WindowGenerator


class FixedDurationWindowGenerator(WindowGenerator):
    """Tile a subtitle into abutting windows of one duration.

    ``window_duration`` is the only size parameter. The window count is however
    many of those windows fit in the subtitle, and the last window is shorter
    when the subtitle length is not an exact multiple.
    """

    def __init__(self, window_duration: timedelta = timedelta(minutes=5)) -> None:
        if window_duration <= timedelta(0):
            raise ValueError("window_duration must be positive")

        self.window_duration = window_duration

    def name(self) -> str:
        return f"Fixed duration temporal({self.window_duration})"

    def generate(self, movie_subtitle: MovieSubtitle) -> list[NarrativeWindow]:
        duration = movie_subtitle.duration
        if duration <= timedelta(0):
            raise ValueError("duration must be positive")

        segments = movie_subtitle.segments
        if not segments:
            return []

        segments = sorted(segments, key=lambda segment: segment.start)
        windows: list[NarrativeWindow] = []
        for index, start in enumerate(self._window_starts(duration)):
            end = min(start + self.window_duration, duration)
            text, from_segment_idx, to_segment_idx = _collect_segments(
                segments, start, end
            )
            windows.append(
                NarrativeWindow(
                    index=index,
                    from_segment_idx=from_segment_idx,
                    to_segment_idx=to_segment_idx,
                    start=start,
                    end=end,
                    text=text,
                )
            )
        return windows

    def _window_starts(self, duration: timedelta) -> list[timedelta]:
        starts: list[timedelta] = []
        start = timedelta(0)
        while start < duration:
            starts.append(start)
            start += self.window_duration
        return starts


def _collect_segments(
    segments: list[SubtitleSegment],
    window_start: timedelta,
    window_end: timedelta,
) -> tuple[str, int | None, int | None]:
    texts: list[str] = []
    segment_from: int | None = None
    segment_to: int | None = None

    for segment in segments:
        if segment.end <= window_start:
            continue
        if segment.start >= window_end:
            break

        if segment_from is None:
            segment_from = segment.segment_idx
        segment_to = segment.segment_idx
        texts.append(segment.content)

    combined_text = " ".join(texts).strip() if texts else ""
    return (combined_text, segment_from, segment_to)
