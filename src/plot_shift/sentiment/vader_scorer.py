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
    """VADER valence as the raw (unnormalized) sum of word scores."""

    @property
    def scorer_name(self) -> str:
        return "vader"

    @property
    def scorer_kind(self) -> ScorerKind:
        return ScorerKind.LEXICON

    def __init__(self) -> None:
        ensure_nltk_data("sentiment/vader_lexicon")
        self._analyzer: SentimentIntensityAnalyzer = SentimentIntensityAnalyzer()
        # NLTK squashes ``compound`` into (-1, 1) via constants.normalize; keep the raw sum.
        self._analyzer.constants.normalize = lambda score, alpha=15: score

    def score_token(self, token: str) -> float:
        if not token:
            return 0.0
        r = self._analyzer.polarity_scores(token)
        score_value = r["compound"]
        if score_value is None:
            return 0.0
        return score_value

    def score(self, text: str) -> Score:
        result = Score()
        result.add_dimension_score(
            DimensionScore(value=self.score_token(text), kind=DimensionKind.VALENCE)
        )
        return result
