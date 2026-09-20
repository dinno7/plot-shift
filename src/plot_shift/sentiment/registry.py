from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from plot_shift.sentiment.base import SentimentScorer
from plot_shift.sentiment.semantic_scorer import TransformerSentimentScorer
from plot_shift.sentiment.vad_scorer import DEFAULT_VAD_LEXICON_PATH, VADLexiconScorer
from plot_shift.sentiment.vader_scorer import VaderLexiconScorer

DEFAULT_SEMANTIC_MODEL_NAME = "cardiffnlp/twitter-roberta-base-sentiment-latest"

# Add a new scoring model by adding one entry here; no other registry code
# to touch. Each factory receives the same kwargs as build_scorer() and may
# ignore the ones it doesn't need.
_SCORER_FACTORIES: dict[str, Callable[..., SentimentScorer]] = {
    "vader": lambda **_: VaderLexiconScorer(),
    "vad": lambda vad_lexicon_file=DEFAULT_VAD_LEXICON_PATH, **_: VADLexiconScorer(
        lexicon_file=vad_lexicon_file
    ),
    "semantic": lambda semantic_model_name=DEFAULT_SEMANTIC_MODEL_NAME,
    semantic_max_length=512,
    **_: TransformerSentimentScorer(
        model_name=semantic_model_name, max_length=semantic_max_length
    ),
}


def list_supported_scorer_strategies() -> tuple[str, ...]:
    return tuple(_SCORER_FACTORIES)


def build_scorer(
    strategy: str,
    vad_lexicon_file: str | Path = DEFAULT_VAD_LEXICON_PATH,
    semantic_model_name: str = DEFAULT_SEMANTIC_MODEL_NAME,
    semantic_max_length: int = 512,
) -> SentimentScorer:
    factory = _SCORER_FACTORIES.get(strategy)
    if factory is None:
        raise ValueError(
            f"Unknown scoring strategy: {strategy}. "
            f"Supported: {', '.join(list_supported_scorer_strategies())}"
        )
    return factory(
        vad_lexicon_file=vad_lexicon_file,
        semantic_model_name=semantic_model_name,
        semantic_max_length=semantic_max_length,
    )
