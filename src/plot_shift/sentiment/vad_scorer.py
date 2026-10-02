"""VAD word-lexicon scorer."""

from pathlib import Path

from plot_shift.sentiment.base import (
    DimensionKind,
    DimensionScore,
    Score,
    ScorerKind,
    SentimentScorer,
)
from plot_shift.sentiment.vad_model import VADIntensityAnalyzer

DEFAULT_VAD_LEXICON_PATH = Path("data/raw/lexicons/vad_lexicon.txt")


class VADLexiconScorer(SentimentScorer):
    @property
    def scorer_name(self) -> str:
        return "vad"

    @property
    def scorer_kind(self) -> ScorerKind:
        return ScorerKind.LEXICON

    def __init__(self, lexicon_file: str | Path = DEFAULT_VAD_LEXICON_PATH) -> None:
        self._analyzer: VADIntensityAnalyzer = VADIntensityAnalyzer(
            lexicon_file=lexicon_file, make_normalize=False
        )

    def score_token(self, token: str) -> dict[DimensionKind, float]:
        if not token:
            return {
                DimensionKind.VALENCE: 0.0,
                DimensionKind.AROUSAL: 0.0,
                DimensionKind.DOMINANCE: 0.0,
            }

        r = self._analyzer.polarity_scores(token)
        valence = r["valence"]["compound"]
        arousal = r["arousal"]["compound"]
        dominance = r["dominance"]["compound"]

        valence = 0.0 if valence is None else valence
        arousal = 0.0 if arousal is None else arousal
        dominance = 0.0 if dominance is None else dominance

        return {
            DimensionKind.VALENCE: valence,
            DimensionKind.AROUSAL: arousal,
            DimensionKind.DOMINANCE: dominance,
        }

    def score(self, text: str) -> Score:
        result = Score()
        scores = self.score_token(text)
        for dimension_kind in scores:
            dimension_score = DimensionScore(value=scores[dimension_kind], kind=dimension_kind)
            result.add_dimension_score(dimension_score)
        return result
