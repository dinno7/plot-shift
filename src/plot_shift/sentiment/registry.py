from __future__ import annotations

from pathlib import Path

from plot_shift.sentiment.base import SentimentScorer
from plot_shift.sentiment.semantic_scorer import TransformerSentimentScorer
from plot_shift.sentiment.vad_scorer import DEFAULT_VAD_LEXICON_PATH, VADLexiconScorer
from plot_shift.sentiment.vader_scorer import VaderLexiconScorer

DEFAULT_SEMANTIC_MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"


def list_supported_scorer_strategies() -> tuple[str, ...]:
    return ("vader", "vad", "semantic")


def build_scorer(
    strategy: str,
    vad_lexicon_file: str | Path = DEFAULT_VAD_LEXICON_PATH,
    semantic_model_name: str = DEFAULT_SEMANTIC_MODEL_NAME,
    semantic_max_length: int = 512,
) -> SentimentScorer:
    if strategy == "vader":
        return VaderLexiconScorer()
    if strategy == "vad":
        return VADLexiconScorer(lexicon_file=vad_lexicon_file)
    if strategy == "semantic":
        return TransformerSentimentScorer(
            model_name=semantic_model_name,
            max_length=semantic_max_length,
        )
    raise ValueError(
        f"Unknown scoring strategy: {strategy}. "
        f"Supported: {', '.join(list_supported_scorer_strategies())}"
    )
