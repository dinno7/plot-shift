"""Transformer-based sentence sentiment scorer."""

from __future__ import annotations

from plot_shift.sentiment.base import DimensionKind, DimensionScore, Score, SentimentScorer


class TransformerSentimentScorer(SentimentScorer):
    """Generic HF classifier mapped to one continuous sentiment score."""

    def __init__(
        self,
        model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest",
        max_length: int = 512,
    ) -> None:
        self._hf_model_name = model_name
        self.model_name = f"semantic:{model_name}"
        self._max_length = max_length

        try:
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except Exception as exc:
            raise RuntimeError(
                "Transformers is required for semantic scoring. "
                "Install with: uv sync --group semantic"
            ) from exc

        self._tokenizer = AutoTokenizer.from_pretrained(model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(model_name)

    def score(self, text: str) -> Score:
        from torch import Tensor
        from torch.nn.functional import softmax

        encoded = self._tokenizer(
            text,
            truncation=True,
            max_length=self._max_length,
            return_tensors="pt",
        )
        output = self._model(**encoded)
        logits: Tensor = output.logits[0]
        probs: Tensor = softmax(logits, dim=-1)
        score_value = self._continuous_score(probs.tolist(), self._model.config.id2label)

        result = Score()
        result.add_dimension_score(DimensionScore(value=score_value, kind=DimensionKind.VALENCE))
        return result

    @staticmethod
    def _continuous_score(probabilities: list[float], id2label: dict[int, str] | None) -> float:
        if id2label:
            label_to_prob = {
                str(label).strip().lower(): probabilities[idx]
                for idx, label in id2label.items()
                if idx < len(probabilities)
            }
            negative = label_to_prob.get("negative", label_to_prob.get("neg"))
            positive = label_to_prob.get("positive", label_to_prob.get("pos"))
            if negative is not None and positive is not None:
                return float(max(-1.0, min(1.0, positive - negative)))

        # Fallback for unknown label sets:
        # binary -> p(class_1) - p(class_0), multi-class -> last - first.
        if len(probabilities) >= 2:
            return float(max(-1.0, min(1.0, probabilities[-1] - probabilities[0])))
        return 0.0


def demo() -> None:
    scorer = TransformerSentimentScorer()
    positive = scorer.score("I loved this movie and the ending was excellent.")
    negative = scorer.score("This film was boring and a complete waste of time.")
    assert positive.dimensions[0].value > negative.dimensions[0].value


if __name__ == "__main__":
    demo()
