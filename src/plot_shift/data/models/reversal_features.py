from dataclasses import dataclass


@dataclass
class ReversalFeatures:
    """Reversal statistics for one (movie, scorer, dimension) triple.

    Produced by running trendet's ``identify_all_trends`` on the windowed
    sentiment series and measuring the direction changes (reversals) and
    their peak-to-trough intensities, matching the Knight et al. methodology.

    Field notes
    -----------
    scorer_name
        Matches ``ModelScore.scorer_name``; stored as ``scorer_name`` in the DB
        (renamed from the old ``model`` column).
    n_windows
        Fixed number of equal-width temporal windows used for every movie so
        that short and long films remain comparable (Knight et al. use 100).
    window_duration
        Duration of each window in seconds for *this* movie.
        Because ``window_duration = total_duration / n_windows``, it varies
        per film and must be stored alongside the results.
    trend_window_size
        The ``window_size`` argument passed to ``trendet.identify_all_trends``.
        This is the *minimum* number of consecutive windows a segment must span
        to be labelled as an Up Trend or Down Trend; shorter segments are
        ignored. Replaces the old ``prominence`` field which was a concept from
        ``scipy.signal.find_peaks`` and does not apply to trendet.
    series_length
        Number of windows that contained at least one scored segment (i.e.
        non-empty buckets).  May be less than ``n_windows`` for short films.
    n_reversals
        Number of Up→Down or Down→Up transitions in the labelled trend series.
    mean_intensity
        Average |peak_value − trough_value| across consecutive reversal pairs,
        as defined by Knight et al.: "average absolute peak-to-trough distance
        in valence between two successive reversal points".
    max_intensity
        Maximum single |peak_value − trough_value| among all reversal pairs.
    """

    imdb_id_int: int
    scorer_name: str
    dimension: str
    n_windows: int
    window_duration: float  # seconds per window for this movie
    trend_window_size: int  # trendet window_size param (min trend length in windows)
    series_length: int
    n_reversals: int
    mean_intensity: float
    max_intensity: float
    detector_name: str
