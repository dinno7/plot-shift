"""Knight et al. (2024) style analysis of reversal features against IMDb rating."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict
from itertools import pairwise

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from scipy import stats

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.services.reversal_service import AGGREGATE_DIMENSION, load_series
from plot_shift.reversals import ReversalDetector, TrendSegment

GROUP = ["scorer_name", "dimension"]
FEATURES = ["n_reversals", "mean_intensity", "max_intensity"]
RATING = "average_rating"
TREND_COLORS = {"up": "tab:purple", "down": "tab:blue"}


def load_features(db: PlotShiftSqliteDB) -> pd.DataFrame:
    """One row per (movie, scorer, dimension) with its IMDb metadata."""
    features = pd.DataFrame([asdict(f) for f in db.reversal_features.list_all()])
    movies = pd.DataFrame([asdict(m) for m in db.movies_meta.get_all()])
    movies = movies[["imdb_id_int", "primary_title", "start_year", "num_votes", RATING]]
    return features.merge(movies, on="imdb_id_int", how="inner")


def summary_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Mean/SD of features and rating per scorer/dimension (Knight's M and SD)."""
    return df.groupby(GROUP)[[*FEATURES, RATING]].agg(["mean", "std"])


def pearson_table(df: pd.DataFrame, features: Sequence[str] = FEATURES) -> pd.DataFrame:
    """Pearson r (and p) of each feature against rating, per scorer/dimension."""
    rows = []
    for (scorer, dim), g in df.groupby(GROUP):
        for feature in features:
            r, p = (math.nan, math.nan)
            if g[feature].nunique() > 1:
                r, p = stats.pearsonr(g[feature], g[RATING])
            rows.append(
                {
                    "scorer_name": scorer,
                    "dimension": dim,
                    "feature": feature,
                    "n": len(g),
                    "r": r,
                    "p": p,
                }
            )
    return pd.DataFrame(rows)


def regression_table(
    df: pd.DataFrame, predictors: Sequence[str] = ("n_reversals", "mean_intensity")
) -> pd.DataFrame:
    """OLS ``rating ~ z(predictors)`` per scorer/dimension, as in Knight's Table 1."""
    rows = []
    for (scorer, dim), g in df.groupby(GROUP):
        x = g[list(predictors)].to_numpy(dtype=float)
        std = x.std(axis=0, ddof=1)
        n, k = len(g), len(predictors) + 1
        if n <= k or (std == 0).any():
            continue
        design = np.column_stack([np.ones(n), (x - x.mean(axis=0)) / std])
        gram = design.T @ design
        if np.linalg.matrix_rank(gram) < k:
            continue
        y = g[RATING].to_numpy(dtype=float)
        beta, *_ = np.linalg.lstsq(design, y, rcond=None)
        resid = y - design @ beta
        dof = n - k
        se = np.sqrt(np.diag(resid @ resid / dof * np.linalg.inv(gram)))
        p = 2 * stats.t.sf(np.abs(beta / se), dof)
        r2 = 1 - (resid @ resid) / np.sum((y - y.mean()) ** 2)

        row: dict[str, object] = {"scorer_name": scorer, "dimension": dim, "n": n}
        for name, b, s, pv in zip(("const", *predictors), beta, se, p, strict=True):
            row |= {f"{name}_coef": b, f"{name}_se": s, f"{name}_p": pv}
        row |= {"r2": r2, "adj_r2": 1 - (1 - r2) * (n - 1) / dof}
        rows.append(row)
    return pd.DataFrame(rows)


def movie_table(df: pd.DataFrame, feature: str = "n_reversals") -> pd.DataFrame:
    """Movies × (scorer, dimension) matrix of ``feature``, sorted by rating."""
    return df.pivot_table(
        index=["imdb_id_int", "primary_title", RATING], columns=GROUP, values=feature
    ).sort_index(level=RATING, ascending=False)


def plot_feature_vs_rating(
    df: pd.DataFrame, feature: str = "n_reversals", ncols: int = 3
) -> Figure:
    """Scatter of ``feature`` vs rating with a least-squares line, one panel per scorer/dimension."""
    groups = list(df.groupby(GROUP))
    nrows = math.ceil(len(groups) / ncols)
    fig, axes = plt.subplots(
        nrows, ncols, figsize=(4 * ncols, 3.2 * nrows), squeeze=False
    )
    for ax, ((scorer, dim), g) in zip(axes.flat, groups, strict=False):
        ax.scatter(g[feature], g[RATING], s=12, alpha=0.6)
        title = f"{scorer} / {dim}"
        if g[feature].nunique() > 1:
            slope, intercept = np.polyfit(g[feature], g[RATING], 1)
            xs = np.linspace(g[feature].min(), g[feature].max(), 2)
            ax.plot(xs, slope * xs + intercept, color="tab:red")
            title += f"  r={stats.pearsonr(g[feature], g[RATING])[0]:.2f}"
        ax.set(title=title, xlabel=feature, ylabel="IMDb rating")
    for ax in axes.flat[len(groups) :]:
        ax.set_visible(False)
    fig.tight_layout()
    return fig


def plot_trajectory(
    ax: Axes, scores: list[float], trends: list[TrendSegment], title: str
) -> None:
    """Knight Fig. 1: the windowed series, colored trends, and reversal extrema."""
    ax.plot(scores, color="lightgray", linewidth=1)
    for t in trends:
        xs = range(t.start, t.end + 1)
        ax.plot(
            xs,
            scores[t.start : t.end + 1],
            color=TREND_COLORS[t.direction],
            linewidth=2,
        )
    points = {
        _extremum_idx(scores, t)
        for a, b in pairwise(trends)
        if a.direction != b.direction
        for t in (a, b)
    }
    ax.scatter(
        sorted(points), [scores[i] for i in sorted(points)], color="tab:red", zorder=3
    )
    ax.set(title=title, xlabel="window", ylabel="score")


def plot_movie(
    db: PlotShiftSqliteDB,
    imdb_id_int: int,
    detector: ReversalDetector,
    scorer_name: str | None = None,
    title: str = "",
    dimension: str | None = None,
) -> Figure:
    """Trajectories of one movie for every scorer/dimension, stacked for comparison.

    ``dimension`` limits the panels to one series, including ``aggregate``.
    """
    imdb_id_int = int(
        imdb_id_int
    )  # sqlite won't match numpy ints coming from DataFrames
    dims_by_scorer: dict[str, list[str]] = {}
    for movie_id, scorer, dim in db.model_scores.list_groups(scorer_name=scorer_name):
        if movie_id == imdb_id_int:
            dims_by_scorer.setdefault(scorer, []).append(dim)
    panels: list[tuple[str, str, list[float]]] = []
    for scorer, dims in dims_by_scorer.items():
        raw_dims = dims
        if dimension is not None and dimension != AGGREGATE_DIMENSION:
            raw_dims = [dim for dim in dims if dim == dimension]
            if not raw_dims:
                continue
        for dim, scores in load_series(db, imdb_id_int, scorer, raw_dims).items():
            if dimension is not None and dim != dimension:
                continue
            panels.append((scorer, dim, scores))

    if not panels:
        fig, ax = plt.subplots(figsize=(10, 2))
        ax.set_axis_off()
        fig.suptitle(title or f"IMDb {imdb_id_int}")
        ax.set_title("no stored scores for this filter")
        return fig

    fig, axes = plt.subplots(
        len(panels), 1, figsize=(10, 2.6 * len(panels)), squeeze=False
    )
    for ax, (scorer, dim, scores) in zip(axes[:, 0], panels, strict=True):
        s = detector.detect(scores)
        plot_trajectory(
            ax,
            scores,
            detector.trends(scores),
            f"{scorer} / {dim}  reversals={s.n_reversals}  mean_int={s.mean_intensity:.3f}",
        )
    fig.suptitle(title or f"IMDb {imdb_id_int}")
    fig.tight_layout()
    return fig


def _extremum_idx(scores: list[float], trend: TrendSegment) -> int:
    segment = scores[trend.start : trend.end + 1]
    pick = max if trend.direction == "up" else min
    return trend.start + segment.index(pick(segment))
