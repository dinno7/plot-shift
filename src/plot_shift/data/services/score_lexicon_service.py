from __future__ import annotations

from pathlib import Path

from plot_shift.data.db import PlotShiftSqliteDB
from plot_shift.data.models import SentenceModelScore
from plot_shift.sentiment import (
    DEFAULT_VAD_LEXICON_PATH,
    SentimentScorer,
    VaderLexiconScorer,
    VADLexiconScorer,
)


class SentenceScoringService:
    def __init__(self, db: PlotShiftSqliteDB, scorer: SentimentScorer) -> None:
        self._db = db
        self._scorer = scorer

    def process(self, batch_size: int = 1000, limit: int | None = None) -> dict[str, int]:
        stats = {
            "movies_total": 0,
            "movies_scored": 0,
            "movies_skipped_empty": 0,
            "sentences_scored": 0,
            "rows_written": 0,
        }

        imdb_ids = self._db.movie_subtitles_meta.list_valid_imdb_ids()
        if limit is not None:
            imdb_ids = imdb_ids[:limit]
        stats["movies_total"] = len(imdb_ids)

        buffer: list[SentenceModelScore] = []
        for imdb_id_int in imdb_ids:
            sentences = self._db.movie_subtitles_meta.list_sentences_by_imdb_id(imdb_id_int)
            if not sentences:
                stats["movies_skipped_empty"] += 1
                continue

            self._db.sentence_model_scores.delete_movie_model(imdb_id_int, self._scorer.model_name)

            for sentence_idx, sentence in enumerate(sentences):
                score = self._scorer.score(sentence)
                stats["sentences_scored"] += 1
                for dimension in score.dimensions:
                    buffer.append(
                        SentenceModelScore(
                            imdb_id_int=imdb_id_int,
                            sentence_idx=sentence_idx,
                            model=self._scorer.model_name,
                            dimension=dimension.kind.value,
                            score=dimension.value,
                        )
                    )
                    if len(buffer) >= batch_size:
                        self._db.sentence_model_scores.insert_many(buffer)
                        stats["rows_written"] += len(buffer)
                        buffer.clear()
            stats["movies_scored"] += 1
        if buffer:
            self._db.sentence_model_scores.insert_many(buffer)
            stats["rows_written"] += len(buffer)
            buffer.clear()

        return stats


def run_score(
    scorer: SentimentScorer,
    db_path: str = "data/proceeded/data.db",
    batch_size: int = 1000,
    limit: int | None = None,
) -> dict[str, int]:
    with PlotShiftSqliteDB(db_path) as db:
        service = SentenceScoringService(db, scorer)
        return service.process(batch_size=batch_size, limit=limit)


def run_score_vader(
    db_path: str = "data/proceeded/data.db",
    batch_size: int = 1000,
    limit: int | None = None,
) -> dict[str, int]:
    return run_score(
        scorer=VaderLexiconScorer(),
        db_path=db_path,
        batch_size=batch_size,
        limit=limit,
    )


def run_score_vad(
    db_path: str = "data/proceeded/data.db",
    batch_size: int = 1000,
    limit: int | None = None,
    lexicon_file: str | Path = DEFAULT_VAD_LEXICON_PATH,
) -> dict[str, int]:
    return run_score(
        scorer=VADLexiconScorer(lexicon_file=lexicon_file),
        db_path=db_path,
        batch_size=batch_size,
        limit=limit,
    )


def run_score_semantic(
    db_path: str = "data/proceeded/data.db",
    batch_size: int = 1000,
    limit: int | None = None,
    model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest",
) -> dict[str, int]:
    # Lazy import keeps non-semantic flows free from torch/transformers.
    from plot_shift.sentiment.semantic_scorer import TransformerSentimentScorer

    return run_score(
        scorer=TransformerSentimentScorer(model_name=model_name),
        db_path=db_path,
        batch_size=batch_size,
        limit=limit,
    )
