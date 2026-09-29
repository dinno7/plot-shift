from __future__ import annotations

import logging
from collections import defaultdict
from statistics import fmean

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.models import ReversalFeatures
from plot_shift.reversals import ReversalDetector, create_reversal_detector

logger = logging.getLogger(__name__)

AGGREGATE_DIMENSION = "aggregate"


def load_series(
    db: PlotShiftSqliteDB, imdb_id_int: int, scorer_name: str, dimensions: list[str]
) -> dict[str, list[float]]:
    """Windowed scores per dimension, plus their per-window mean when there are several."""
    series = {
        dim: [r.score for r in db.model_scores.list_windowed(imdb_id_int, scorer_name, dim)]
        for dim in dimensions
    }
    if len(series) > 1:
        series[AGGREGATE_DIMENSION] = [
            fmean(values) for values in zip(*series.values(), strict=True)
        ]
    return series


class ReversalService:
    def __init__(
        self,
        db: PlotShiftSqliteDB,
        detector: ReversalDetector,
        trend_window_size: int,
        window_seconds: float,
    ) -> None:
        self._db = db
        self._detector = detector
        self._trend_window_size = trend_window_size
        self._window_seconds = window_seconds

    def process(
        self,
        scorer_name: str | None = None,
        dimension: str | None = None,
        limit_movies: int | None = None,
    ) -> dict[str, int]:
        stats = {"movie_scorers": 0, "rows_written": 0}

        dims_by_movie_scorer: dict[tuple[int, str], list[str]] = defaultdict(list)
        for imdb_id_int, scorer, dim in self._db.model_scores.list_groups(
            scorer_name=scorer_name, limit_movies=limit_movies
        ):
            dims_by_movie_scorer[(imdb_id_int, scorer)].append(dim)

        for (imdb_id_int, scorer), dims in dims_by_movie_scorer.items():
            features: list[ReversalFeatures] = []
            for dim, scores in load_series(self._db, imdb_id_int, scorer, dims).items():
                if dimension is not None and dim != dimension:
                    continue
                result = self._detector.detect(scores)
                features.append(
                    ReversalFeatures(
                        imdb_id_int=imdb_id_int,
                        scorer_name=scorer,
                        dimension=dim,
                        n_windows=len(scores),
                        window_duration=self._window_seconds,
                        trend_window_size=self._trend_window_size,
                        series_length=result.series_length,
                        n_reversals=result.n_reversals,
                        mean_intensity=result.mean_intensity,
                        max_intensity=result.max_intensity,
                        detector_name=self._detector.name,
                    )
                )
            self._db.reversal_features.upsert_many(features)
            logger.info("IMDB(%d) %s: %d reversal rows", imdb_id_int, scorer, len(features))
            stats["movie_scorers"] += 1
            stats["rows_written"] += len(features)

        return stats


def run_extract_reversals(
    db_path: str = "data/proceeded/data.db",
    scorer_name: str | None = None,
    dimension: str | None = None,
    limit_movies: int | None = None,
    detector: str = "ruptures",
    trend_window_size: int = 5,
    ruptures_penalty: float = 1.0,
    window_seconds: float = 300,
) -> dict[str, int]:
    reversal_detector = create_reversal_detector(
        detector, window_size=trend_window_size, ruptures_penalty=ruptures_penalty
    )
    with PlotShiftSqliteDB(db_path) as db:
        service = ReversalService(db, reversal_detector, trend_window_size, window_seconds)
        return service.process(
            scorer_name=scorer_name, dimension=dimension, limit_movies=limit_movies
        )
