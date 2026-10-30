from datetime import timedelta

import pytest

from plot_shift.data.models import MovieSubtitle, SubtitleSegment
from plot_shift.windows import FixedDurationWindowGenerator, create_window_generator
from plot_shift.windows.fixed_width_duration import FixedWidthAndDurationWindowGenerator


def _movie(spans: list[tuple[int, int, str]]) -> MovieSubtitle:
    segments = [
        SubtitleSegment(
            imdb_id_int=1,
            segment_idx=index,
            start=timedelta(minutes=start),
            end=timedelta(minutes=end),
            content=text,
        )
        for index, (start, end, text) in enumerate(spans)
    ]
    return MovieSubtitle(imdb_id=1, words=[], segments=segments)


def test_count_follows_subtitle_length() -> None:
    movie = _movie([(0, 12, "hello")])
    windows = FixedDurationWindowGenerator(timedelta(minutes=5)).generate(movie)

    assert [(window.start, window.end) for window in windows] == [
        (timedelta(minutes=0), timedelta(minutes=5)),
        (timedelta(minutes=5), timedelta(minutes=10)),
        (timedelta(minutes=10), timedelta(minutes=12)),
    ]
    assert [window.index for window in windows] == [0, 1, 2]


def test_exact_multiple_has_no_short_tail() -> None:
    movie = _movie([(0, 10, "hello")])
    windows = FixedDurationWindowGenerator(timedelta(minutes=5)).generate(movie)

    assert len(windows) == 2
    assert all(window.end - window.start == timedelta(minutes=5) for window in windows)
    assert windows[-1].end == movie.duration


def test_subtitle_shorter_than_one_window_is_a_single_window() -> None:
    movie = _movie([(0, 3, "hello")])
    windows = FixedDurationWindowGenerator(timedelta(minutes=5)).generate(movie)

    assert len(windows) == 1
    assert windows[0].start == timedelta(0)
    assert windows[0].end == timedelta(minutes=3)
    assert windows[0].text == "hello"


def test_segment_on_a_boundary_is_included_in_both_windows() -> None:
    movie = _movie(
        [
            (0, 2, "early"),
            (4, 6, "across"),
            (11, 12, "late"),
        ]
    )
    windows = FixedDurationWindowGenerator(timedelta(minutes=5)).generate(movie)

    assert windows[0].text == "early across"
    assert (windows[0].from_segment_idx, windows[0].to_segment_idx) == (0, 1)
    assert windows[1].text == "across"
    assert (windows[1].from_segment_idx, windows[1].to_segment_idx) == (1, 1)
    assert windows[2].text == "late"


def test_gap_still_emits_an_empty_window() -> None:
    movie = _movie([(0, 1, "open"), (11, 12, "close")])
    windows = FixedDurationWindowGenerator(timedelta(minutes=5)).generate(movie)

    assert windows[1].text == ""
    assert windows[1].from_segment_idx is None
    assert windows[1].to_segment_idx is None
    assert windows[1].start == timedelta(minutes=5)
    assert windows[1].end == timedelta(minutes=10)


def test_segments_are_ordered_by_start_before_collection() -> None:
    movie = _movie([(6, 8, "second"), (1, 2, "first")])
    windows = FixedDurationWindowGenerator(timedelta(minutes=5)).generate(movie)

    assert windows[0].text == "first"
    assert windows[1].text == "second"


def test_rejects_non_positive_duration() -> None:
    with pytest.raises(ValueError, match="window_duration"):
        FixedDurationWindowGenerator(timedelta(0))

    movie = _movie([(0, 0, "empty")])
    with pytest.raises(ValueError, match="duration must be positive"):
        FixedDurationWindowGenerator(timedelta(minutes=5)).generate(movie)


def test_create_window_generator_selects_implementation() -> None:
    duration = timedelta(minutes=5)
    fixed_duration = create_window_generator("fixed-duration", window_duration=duration)
    fixed_width = create_window_generator(
        "fixed-width-duration", window_duration=duration, n_windows=100
    )

    assert isinstance(fixed_duration, FixedDurationWindowGenerator)
    assert isinstance(fixed_width, FixedWidthAndDurationWindowGenerator)
    assert fixed_duration.window_duration == duration
    assert fixed_width.n_windows == 100


def test_create_window_generator_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="unknown window generator"):
        create_window_generator("sliding")
