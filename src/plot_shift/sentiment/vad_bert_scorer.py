from dataclasses import dataclass, field

import torch
from notebooks.colab_scorer import DimensionKind, ScorerKind
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from plot_shift.sentiment import DimensionScore, Score, SentimentScorer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unit_to_pm1(value: float, lo: float, hi: float) -> float:
    """Clip ``value`` into [lo, hi] and linearly map it onto [-1, 1]."""
    clipped = max(lo, min(hi, float(value)))
    return 2.0 * (clipped - lo) / (hi - lo) - 1.0


# ---------------------------------------------------------------------------
# 1) Multi-dimensional VAD transformer scorer (recommended)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VadBertScorer(SentimentScorer):
    """Multi-dimensional (VAD) transformer scorer built on ``RobroKools/vad-bert``.

    The model regresses Valence, Arousal and Dominance from text. Its raw
    outputs are approximately on a [0, 1] scale; anything outside the range
    is clipped and the values are re-scaled to the required [-1, 1] interval
    (valence 0 -> -1 = maximally unpleasant, 1 -> +1 = maximally pleasant,
    and likewise for arousal/calm-excited and dominance/controlled-in-control).
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
        """Return the three VAD dimension scores for ``text``, each in [-1, 1]."""
        inputs = self._tokenizer(text, return_tensors="pt", truncation=True, max_length=512).to(
            self.device
        )
        with torch.no_grad():
            logits = self._model(**inputs).logits.detach().squeeze().tolist()

        valence, arousal, dominance = (_unit_to_pm1(v, 0.0, 1.0) for v in logits)

        score = Score()
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
