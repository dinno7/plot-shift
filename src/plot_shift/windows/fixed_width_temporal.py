from datetime import timedelta

from plot_shift.data import PlotShiftSqliteDB
from plot_shift.data.models import MovieSubtitle, NarrativeWindow, SubtitleSegment
from plot_shift.windows import WindowGenerator


class FixedWidthTemporalWindowGenerator(WindowGenerator):
    def __init__(
        self,
        window_duration: timedelta = timedelta(minutes=5),
        n_windows: int = 100,
    ):
        if window_duration <= timedelta(0):
            raise ValueError("window_duration must be positive")

        if n_windows <= 0:
            raise ValueError("n_windows must be positive")

        self.window_duration = window_duration
        self.n_windows = n_windows

    def name(self) -> str:
        return f"Fixed width({self.n_windows}) temporal({self.window_duration.__str__()})"

    def generate(
        self,
        movie_subtitle: MovieSubtitle,
    ) -> list[NarrativeWindow]:
        duration = movie_subtitle.duration

        if duration <= timedelta(0):
            raise ValueError("duration must be positive")

        segments = movie_subtitle.segments
        if not segments:
            return []

        segments = sorted(
            segments,
            key=lambda segment: segment.start,
        )

        starts = self._calculate_window_starts(duration)

        windows: list[NarrativeWindow] = []
        for index, start in enumerate(starts):
            text, from_segment_idx, to_segment_idx = self._collect_segments(
                segments,
                start,
                min(start + self.window_duration, duration),
            )
            if from_segment_idx is None or to_segment_idx is None:
                continue

            windows.append(
                NarrativeWindow(
                    index=index,
                    from_segment_idx=from_segment_idx,
                    to_segment_idx=to_segment_idx,
                    start=start,
                    end=min(
                        start + self.window_duration,
                        duration,
                    ),
                    text=text,
                )
            )

        return windows

    def _calculate_window_starts(
        self,
        duration: timedelta,
    ) -> list[timedelta]:

        if duration <= self.window_duration:
            return [timedelta(0)]

        max_start = duration - self.window_duration

        if self.n_windows == 1:
            return [timedelta(0)]

        stride = max_start / (self.n_windows - 1)

        return [stride * i for i in range(self.n_windows)]

    def _collect_segments(
        self,
        segments: list[SubtitleSegment],
        window_start: timedelta,
        window_end: timedelta,
    ) -> tuple[str, int | None, int | None]:

        texts: list[str] = []
        segment_from: int | None = None
        segment_to: int | None = None

        for segment in segments:
            # Segment ends before the window starts.
            if segment.end <= window_start:
                continue

            # Segment starts after the window ends.
            if segment.start >= window_end:
                break

            # The first segment
            if segment_from is None:
                segment_from = segment.segment_idx
            segment_to = segment.segment_idx
            texts.append(segment.content)

        combined_text = " ".join(texts).strip() if texts else ""
        return (combined_text, segment_from, segment_to)


# Example
if __name__ == "__main__":
    with PlotShiftSqliteDB("data/proceeded/data.db") as repo:
        windower = FixedWidthTemporalWindowGenerator(timedelta(minutes=5), n_windows=100)
        movie_sub = repo.movie_subtitles.find_by_imdb_id(31381)
        if movie_sub is None:
            raise ValueError("MovieSubtitle is None")
        windows = windower.generate(movie_subtitle=movie_sub)
        for w in windows:
            print("Window > ", w)
            print("-----\n")
        print("LEN", len(windows))
