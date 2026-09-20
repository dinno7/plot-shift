"""VAD word-lexicon scorer."""

from pathlib import Path

from plot_shift.sentiment.base import DimensionKind, DimensionScore, Score, SentimentScorer
from plot_shift.sentiment.vad_model import VADIntensityAnalyzer

DEFAULT_VAD_LEXICON_PATH = Path("data/raw/lexicons/vad_lexicon.txt")


class VADLexiconScorer(SentimentScorer):
    model_name = "vad"

    def __init__(self, lexicon_file: str | Path = DEFAULT_VAD_LEXICON_PATH) -> None:
        self._analyzer: VADIntensityAnalyzer = VADIntensityAnalyzer(lexicon_file=lexicon_file)

    def score_token(self, token: str) -> dict[DimensionKind, float]:
        r = self._analyzer.polarity_scores(token)
        # NOTE: It is always in range of (-1, +1)
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
        if not text:  # Empty text
            return result
        scores = self.score_token(text)
        for dimension_kind in scores:
            dimension_score = DimensionScore(value=scores[dimension_kind], kind=dimension_kind)
            result.add_dimension_score(dimension_score)
        return result
