"""Inspect stored scores and reversal features across scorers and detectors.

The Knight tables live in ``reversal_report``. This module picks movies, correlates
windowed series, and runs a ``ReversalDetector`` in memory without writing.
"""

from __future__ import annotations

import math
import random
from collections import defaultdict
from collections.abc import Sequence

import pandas as pd
from matplotlib.figure import Figure
from scipy import stats

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.services.reversal_service import AGGREGATE_DIMENSION, load_series
from plot_shift.evaluation.reversal_report import plot_movie
from plot_shift.reversals import ReversalDetector

_COVERAGE_COLUMNS = [
    "scorer_name",
    "dimension",
    "detector_name",
    "n_movies",
    "n_windows_min",
    "n_windows_max",
    "window_duration_min",
    "window_duration_max",
    "trend_window_size_min",
    "trend_window_size_max",
]

_LIVE_COLUMNS = [
    "imdb_id_int",
    "primary_title",
    "scorer_name",
    "dimension",
    "detector_name",
    "n_windows",
    "n_reversals",
    "mean_intensity",
    "max_intensity",
]

_AGREEMENT_COLUMNS = [
    "imdb_id_int",
    "primary_title",
    "scorer_a",
    "dimension_a",
    "scorer_b",
    "dimension_b",
    "n_windows",
    "aligned",
    "r",
    "p",
]

_AGREEMENT_SUMMARY_COLUMNS = [
    "scorer_a",
    "dimension_a",
    "scorer_b",
    "dimension_b",
    "n_movies",
    "mean_r",
]


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    """Movie counts and stored window settings per scorer, dimension, and detector."""
    if df.empty:
        return pd.DataFrame(columns=_COVERAGE_COLUMNS)
    return (
        df.groupby(["scorer_name", "dimension", "detector_name"], dropna=False)
        .agg(
            n_movies=("imdb_id_int", "nunique"),
            n_windows_min=("n_windows", "min"),
            n_windows_max=("n_windows", "max"),
            window_duration_min=("window_duration", "min"),
            window_duration_max=("window_duration", "max"),
            trend_window_size_min=("trend_window_size", "min"),
            trend_window_size_max=("trend_window_size", "max"),
        )
        .reset_index()
    )


def pick_movies(
    df: pd.DataFrame,
    n: int,
    seed: int,
    pinned_ids: Sequence[int],
) -> list[int]:
    """Pinned IMDb ids first, then ``n`` other movies from ``df``.

    The same ``seed`` returns the same random movies. Pinned ids are kept even
    when they are absent from ``df``, so a fixed case can be replotted after a
    filter change. ``df`` must contain ``imdb_id_int``.
    """
    if n < 0:
        raise ValueError("n must be >= 0")

    pinned: list[int] = []
    seen: set[int] = set()
    for imdb_id in pinned_ids:
        imdb_id = int(imdb_id)
        if imdb_id not in seen:
            pinned.append(imdb_id)
            seen.add(imdb_id)

    available = sorted({int(movie_id) for movie_id in df["imdb_id_int"]} - seen)
    chosen = random.Random(seed).sample(available, min(n, len(available)))
    return pinned + chosen


def series_agreement(
    db: PlotShiftSqliteDB,
    imdb_ids: Sequence[int],
    scorer_name: str | None = None,
    dimension: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pearson *r* between windowed series of each scorer/dimension pair.

    Returns ``(detail, summary)``. ``detail`` is one row per movie and pair.
    ``summary`` is the mean *r* of each pair across movies. Unaligned series
    (different window counts) are kept in ``detail`` with ``aligned=False`` and
    are left out of the mean.
    """
    titles = _titles(db)
    by_movie = _series_by_movie(db, imdb_ids, scorer_name, dimension)
    rows: list[dict[str, object]] = []
    for imdb_id in _unique_ids(imdb_ids):
        series = by_movie.get(imdb_id, {})
        labels = sorted(series)
        for index, left in enumerate(labels):
            for right in labels[index + 1 :]:
                left_scores = series[left]
                right_scores = series[right]
                aligned = len(left_scores) == len(right_scores)
                r, p = _pearson(left_scores, right_scores) if aligned else (math.nan, math.nan)
                rows.append(
                    {
                        "imdb_id_int": imdb_id,
                        "primary_title": titles.get(imdb_id, ""),
                        "scorer_a": left[0],
                        "dimension_a": left[1],
                        "scorer_b": right[0],
                        "dimension_b": right[1],
                        "n_windows": len(left_scores) if aligned else math.nan,
                        "aligned": aligned,
                        "r": r,
                        "p": p,
                    }
                )

    detail = pd.DataFrame(rows, columns=_AGREEMENT_COLUMNS)
    if detail.empty:
        return detail, pd.DataFrame(columns=_AGREEMENT_SUMMARY_COLUMNS)

    summary = (
        detail.groupby(
            ["scorer_a", "dimension_a", "scorer_b", "dimension_b"],
            dropna=False,
        )
        .agg(n_movies=("r", "count"), mean_r=("r", "mean"))
        .reset_index()
        .sort_values("mean_r", ascending=False, ignore_index=True)
    )
    return detail, summary


def live_stats(
    db: PlotShiftSqliteDB,
    imdb_ids: Sequence[int],
    detector: ReversalDetector,
    scorer_name: str | None = None,
    dimension: str | None = None,
) -> pd.DataFrame:
    """Reversal stats from ``detector`` on stored series. Does not write."""
    titles = _titles(db)
    by_movie = _series_by_movie(db, imdb_ids, scorer_name, dimension)
    rows: list[dict[str, object]] = []
    for imdb_id in _unique_ids(imdb_ids):
        for (scorer, dim), scores in sorted(by_movie.get(imdb_id, {}).items()):
            result = detector.detect(scores)
            rows.append(
                {
                    "imdb_id_int": imdb_id,
                    "primary_title": titles.get(imdb_id, ""),
                    "scorer_name": scorer,
                    "dimension": dim,
                    "detector_name": detector.name,
                    "n_windows": len(scores),
                    "n_reversals": result.n_reversals,
                    "mean_intensity": result.mean_intensity,
                    "max_intensity": result.max_intensity,
                }
            )
    return pd.DataFrame(rows, columns=_LIVE_COLUMNS)


def plot_cases(
    db: PlotShiftSqliteDB,
    imdb_ids: Sequence[int],
    detector: ReversalDetector,
    scorer_name: str | None = None,
    dimension: str | None = None,
) -> list[Figure]:
    """One trajectory figure per movie, using ``detector`` on stored windows."""
    titles = _titles(db)
    figures: list[Figure] = []
    for imdb_id in _unique_ids(imdb_ids):
        name = titles.get(imdb_id, "")
        label = f"{name} ({imdb_id})" if name else f"IMDb {imdb_id}"
        figures.append(
            plot_movie(
                db,
                imdb_id,
                detector,
                scorer_name=scorer_name,
                dimension=dimension,
                title=f"{label}  [{detector.name}]",
            )
        )
    return figures


def _series_by_movie(
    db: PlotShiftSqliteDB,
    imdb_ids: Sequence[int],
    scorer_name: str | None,
    dimension: str | None,
) -> dict[int, dict[tuple[str, str], list[float]]]:
    wanted = set(_unique_ids(imdb_ids))
    dims_by_movie_scorer: dict[tuple[int, str], list[str]] = defaultdict(list)
    for movie_id, scorer, dim in db.model_scores.list_groups(scorer_name=scorer_name):
        if movie_id in wanted:
            dims_by_movie_scorer[(movie_id, scorer)].append(dim)

    by_movie: dict[int, dict[tuple[str, str], list[float]]] = {movie_id: {} for movie_id in wanted}
    for (movie_id, scorer), dims in dims_by_movie_scorer.items():
        raw_dims = dims
        if dimension is not None and dimension != AGGREGATE_DIMENSION:
            raw_dims = [dim for dim in dims if dim == dimension]
            if not raw_dims:
                continue
        loaded = load_series(db, movie_id, scorer, raw_dims)
        for dim, scores in loaded.items():
            if dimension is not None and dim != dimension:
                continue
            by_movie[movie_id][(scorer, dim)] = scores
    return by_movie


def _titles(db: PlotShiftSqliteDB) -> dict[int, str]:
    titles: dict[int, str] = {}
    for movie in db.movies_meta.get_all():
        if movie.imdb_id_int is not None:
            titles[int(movie.imdb_id_int)] = movie.primary_title
    return titles


def _unique_ids(imdb_ids: Sequence[int]) -> list[int]:
    unique: list[int] = []
    seen: set[int] = set()
    for imdb_id in imdb_ids:
        imdb_id = int(imdb_id)
        if imdb_id not in seen:
            unique.append(imdb_id)
            seen.add(imdb_id)
    return unique


def _pearson(left: list[float], right: list[float]) -> tuple[float, float]:
    if len(left) < 2 or len(left) != len(right):
        return math.nan, math.nan
    if len(set(left)) < 2 or len(set(right)) < 2:
        return math.nan, math.nan
    r, p = stats.pearsonr(left, right)
    return float(r), float(p)
