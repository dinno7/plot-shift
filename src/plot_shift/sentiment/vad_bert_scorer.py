from dataclasses import dataclass, field

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from plot_shift.sentiment.base import (
    DimensionKind,
    DimensionScore,
    Score,
    ScorerKind,
    SentimentScorer,
)

# ---------------------------------------------------------------------------
# 1) Multi-dimensional VAD transformer scorer (recommended)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VadBertScorer(SentimentScorer):
    """Multi-dimensional (VAD) transformer scorer built on ``RobroKools/vad-bert``.

    The model regresses Valence, Arousal and Dominance from text; the raw
    regression outputs (approximately on a [0, 1] scale) are returned as-is.
    """

    model_name: str = "RobroKools/vad-bert"
    device: str = field(default="cuda" if torch.cuda.is_available() else "cpu")
    _tokenizer: object = field(default=None, init=False, repr=False, compare=False)
    _model: object = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        model.to(self.device)
        model.eval()
        # frozen dataclass -> assign via object.__setattr__
        object.__setattr__(self, "_tokenizer", tokenizer)
        object.__setattr__(self, "_model", model)

    def score(self, text: str) -> Score:
        score = Score()
        if not text or not text.strip():
            score.add_dimension_score(DimensionScore(value=0.0, kind=DimensionKind.VALENCE))
            score.add_dimension_score(DimensionScore(value=0.0, kind=DimensionKind.AROUSAL))
            score.add_dimension_score(DimensionScore(value=0.0, kind=DimensionKind.DOMINANCE))
            return score

        """Return the three raw VAD dimension scores for ``text``."""
        inputs = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(
            self.device
        )
        with torch.no_grad():
            logits = self._model(**inputs).logits.detach().squeeze().tolist()

        valence, arousal, dominance = logits

        score.add_dimension_score(DimensionScore(value=valence, kind=DimensionKind.VALENCE))
        score.add_dimension_score(DimensionScore(value=arousal, kind=DimensionKind.AROUSAL))
        score.add_dimension_score(DimensionScore(value=dominance, kind=DimensionKind.DOMINANCE))
        return score

    @property
    def scorer_name(self) -> str:
        return "vad-bert"

    @property
    def scorer_kind(self) -> ScorerKind:
        return ScorerKind.TRANSFORMER
