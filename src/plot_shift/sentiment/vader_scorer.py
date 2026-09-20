"""VADER word-lexicon scorer (Knight baseline)."""

from nltk.sentiment.vader import SentimentIntensityAnalyzer

from plot_shift.data.utils import ensure_nltk_data
from plot_shift.sentiment.base import (
    DimensionKind,
    DimensionScore,
    Score,
    ScorerKind,
    SentimentScorer,
)


class VaderLexiconScorer(SentimentScorer):
    """Lookup VADER lexicon valence; map roughly [-4, 4] to [-1, 1]."""

    @property
    def scorer_name(self) -> str:
        return "vad"

    @property
    def scorer_kind(self) -> ScorerKind:
        return ScorerKind.LEXICON

    def __init__(self) -> None:
        ensure_nltk_data("sentiment/vader_lexicon")
        self._analyzer: SentimentIntensityAnalyzer = SentimentIntensityAnalyzer()

    def score_token(self, token: str) -> float:
        r = self._analyzer.polarity_scores(token)
        score_value = r["compound"]  # NOTE: It is always in range of (-1, +1)
        if score_value is None:
            return 0.0
        return score_value

    def score(self, text: str) -> Score:
        result = Score()
        if not text:  # Empty text
            return result
        result.add_dimension_score(
            DimensionScore(value=self.score_token(text), kind=DimensionKind.VALENCE)
        )
        return result
