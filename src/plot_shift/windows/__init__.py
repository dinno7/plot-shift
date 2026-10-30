from datetime import timedelta

from .base import WindowGenerator
from .fixed_duration import FixedDurationWindowGenerator
from .fixed_width_duration import FixedWidthAndDurationWindowGenerator

__all__ = [
    "FixedDurationWindowGenerator",
    "FixedWidthAndDurationWindowGenerator",
    "WindowGenerator",
    "create_window_generator",
]


def create_window_generator(
    name: str,
    *,
    window_duration: timedelta = timedelta(minutes=5),
    n_windows: int = 100,
) -> WindowGenerator:
    """Build a window generator by name.

    ``fixed-width-duration`` places ``n_windows`` windows of ``window_duration`` across
    the subtitle. ``fixed-duration`` places abutting windows of
    ``window_duration`` and lets the count follow the subtitle length.
    """

    key = name.strip().lower()
    if key == "fixed-width-duration":
        return FixedWidthAndDurationWindowGenerator(window_duration, n_windows)
    if key == "fixed-duration":
        return FixedDurationWindowGenerator(window_duration)
    raise ValueError(
        f"unknown window generator: {name!r} (expected fixed-width-duration or fixed-duration)"
    )
