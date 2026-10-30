"""DistilBERT SST-2 sequence classifier as a single valence score."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from plot_shift.sentiment.base import (
    DimensionKind,
    DimensionScore,
    Score,
    ScorerKind,
    SentimentScorer,
)

DISTILBERT_SST2_MODEL = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
DISTILBERT_SST2_SCORER_NAME = "distilbert-sst2"


def class_index(id2label: Mapping[Any, str], label: str) -> int:
    """Return the logit index whose label matches ``label``."""
    wanted = label.upper()
    for raw_index, name in id2label.items():
        if str(name).upper() == wanted:
            return int(raw_index)
    raise ValueError(f"Model has no {label} label: {dict(id2label)}")


def signed_sst2_valence(negative: float, positive: float) -> float:
    """Map SST-2 class probabilities to a valence in [-1, 1]."""
    return positive - negative


@dataclass(frozen=True)
class DistilBertSst2Scorer(SentimentScorer):
    """Valence from ``distilbert/distilbert-base-uncased-finetuned-sst-2-english``.

    The model is a binary SST-2 classifier. Valence is ``P(POSITIVE) - P(NEGATIVE)``,
    so a confident positive sentence scores near 1 and a confident negative sentence
    scores near -1.
    """

    model_name: str = DISTILBERT_SST2_MODEL
    max_length: int = 512
    device: str = field(default="cuda" if torch.cuda.is_available() else "cpu")
    _tokenizer: Any = field(default=None, init=False, repr=False, compare=False)
    _model: Any = field(default=None, init=False, repr=False, compare=False)
    _negative_index: int = field(default=0, init=False, repr=False, compare=False)
    _positive_index: int = field(default=1, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        model.to(self.device)
        model.eval()
        id2label = model.config.id2label
        object.__setattr__(self, "_tokenizer", tokenizer)
        object.__setattr__(self, "_model", model)
        object.__setattr__(self, "_negative_index", class_index(id2label, "NEGATIVE"))
        object.__setattr__(self, "_positive_index", class_index(id2label, "POSITIVE"))

    def score(self, text: str) -> Score:
        result = Score()
        if not text or not text.strip():
            result.add_dimension_score(DimensionScore(value=0.0, kind=DimensionKind.VALENCE))
            return result

        inputs = self._tokenizer(
            text, return_tensors="pt", truncation=True, max_length=self.max_length
        ).to(self.device)
        with torch.no_grad():
            logits = self._model(**inputs).logits
            probabilities = torch.softmax(logits, dim=-1).squeeze(0)

        negative = float(probabilities[self._negative_index])
        positive = float(probabilities[self._positive_index])
        result.add_dimension_score(
            DimensionScore(
                value=signed_sst2_valence(negative, positive),
                kind=DimensionKind.VALENCE,
            )
        )
        return result

    @property
    def scorer_name(self) -> str:
        return DISTILBERT_SST2_SCORER_NAME

    @property
    def scorer_kind(self) -> ScorerKind:
        return ScorerKind.TRANSFORMER
