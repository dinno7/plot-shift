from __future__ import annotations

import logging
from datetime import timedelta
from pathlib import Path

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.models import ModelScore
from plot_shift.sentiment import (
    DEFAULT_VAD_LEXICON_PATH,
    SentimentScorer,
    VaderLexiconScorer,
    VADLexiconScorer,
)
from plot_shift.windows.base import WindowGenerator
from plot_shift.windows.fixed_width_temporal import FixedWidthTemporalWindowGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())


class ScoringService:
    def __init__(
        self, db: PlotShiftSqliteDB, window_generator: WindowGenerator, scorer: SentimentScorer
    ) -> None:
        self._db = db
        self._scorer = scorer
        self._window_generator = window_generator

    def process(self, batch_size: int = 1000, limit: int | None = None) -> dict[str, int]:
        stats = {
            "movies_total": 0,
            "movies_scored": 0,
            "movies_skipped_empty": 0,
            "sentences_scored": 0,
            "rows_written": 0,
        }

        imdb_ids = self._db.movie_subtitles.list_valid_imdb_ids()
        if limit is not None:
            imdb_ids = imdb_ids[:limit]
        stats["movies_total"] = len(imdb_ids)

        buffer: list[ModelScore] = []
        for imdb_id_int in imdb_ids:
            logger.info("Start scoring IMDB(%d) movie", imdb_id_int)
            movie_subtitle = self._db.movie_subtitles.find_by_imdb_id(imdb_id_int)
            if movie_subtitle is None:
                logger.warning("Movie with IMDB(%d) is not exists, ignored", imdb_id_int)
                continue

            logger.info(
                "Generating windows IMDB(%d) with %s window generator",
                imdb_id_int,
                self._window_generator.name(),
            )
            windows = self._window_generator.generate(movie_subtitle)
            logger.info("Scoring %d windows with %s model", len(windows), self._scorer.scorer_name)
            for window in windows:
                score = self._scorer.score(window.text)
                stats["sentences_scored"] += 1
                for dimension in score.dimensions:
                    buffer.append(
                        ModelScore(
                            imdb_id_int=imdb_id_int,
                            from_segment_idx=window.from_segment_idx,
                            to_segment_idx=window.to_segment_idx,
                            window_idx=window.index,
                            total_windows=len(windows),
                            scorer_name=self._scorer.scorer_name,
                            scorer_kind=self._scorer.scorer_kind.value,
                            dimension=dimension.kind.value,
                            score=dimension.value,
                        )
                    )
                    if len(buffer) >= batch_size:
                        self._db.model_scores.insert_many(buffer)
                        stats["rows_written"] += len(buffer)
                        buffer.clear()

            stats["movies_scored"] += 1
        if len(buffer) > 0:
            self._db.model_scores.insert_many(buffer)
            stats["rows_written"] += len(buffer)
            buffer.clear()

        return stats


DEFAULT_SEMANTIC_MODEL_NAME = "vad"


def run_score(
    scorer: SentimentScorer,
    window_generator: WindowGenerator,
    db_path: str = "data/proceeded/data.db",
    batch_size: int = 1000,
    limit: int | None = None,
) -> dict[str, int]:
    with PlotShiftSqliteDB(db_path) as db:
        service = ScoringService(db, window_generator, scorer)
        return service.process(batch_size=batch_size, limit=limit)


def run_score_model(
    model: str,
    db_path: str = "data/proceeded/data.db",
    batch_size: int = 1000,
    limit: int | None = None,
    window_duration: timedelta = timedelta(minutes=5),
    n_windows: int = 100,
    vad_lexicon_file: str | Path = DEFAULT_VAD_LEXICON_PATH,
    semantic_model_name: str = DEFAULT_SEMANTIC_MODEL_NAME,
    semantic_max_length: int = 512,
) -> dict[str, int]:
    scorer: SentimentScorer
    selected_model = model.strip(" ").lower()
    if selected_model == "vader":
        scorer = VaderLexiconScorer()
    elif selected_model == "vad":
        scorer = VADLexiconScorer(lexicon_file=vad_lexicon_file)
    else:
        raise ValueError(
            f"Unknown scoring strategy: {model}. ",
            f"Supported: {list_supported_scorer()}",
        )

    window_generator = FixedWidthTemporalWindowGenerator(window_duration, n_windows)
    return run_score(
        scorer=scorer,
        window_generator=window_generator,
        db_path=db_path,
        batch_size=batch_size,
        limit=limit,
    )


def list_supported_scorer() -> list[str]:
    return ["vader", "vad"]
