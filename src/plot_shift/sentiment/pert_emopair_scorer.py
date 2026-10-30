from pathlib import Path

import torch
from huggingface_hub import snapshot_download
from torch import nn
from transformers import AutoTokenizer, RobertaModel

from plot_shift.sentiment.base import (
    DimensionKind,
    DimensionScore,
    Score,
    ScorerKind,
    SentimentScorer,
)
from plot_shift.sentiment.scales import emobank_to_bipolar


class RoBERTaForVAD(nn.Module):
    """
    Architecture used by PERT-EmoPair.

    RoBERTa-large encoder + dropout + linear regression head
    producing Valence, Arousal and Dominance.
    """

    def __init__(self, base_model_name: str = "roberta-large"):
        super().__init__()

        self.base_model = RobertaModel.from_pretrained(base_model_name)

        self.dropout = nn.Dropout(p=0.1)

        self.regressor = nn.Linear(
            self.base_model.config.hidden_size,
            3,
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> torch.Tensor:

        outputs = self.base_model(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )

        # First token = <s> / CLS equivalent for RoBERTa
        cls = self.dropout(outputs.last_hidden_state[:, 0, :])

        return self.regressor(cls)


class PERTEmoPairScorer(SentimentScorer):
    """PERT-EmoPair valence, arousal, and dominance on [-1, 1].

    Valence is trained against EmoBank's 1–5 ratings, so it is mapped with
    ``emobank_to_bipolar``. Arousal and dominance are trained against the
    EmoPair Bradley-Terry scores, which the dataset already stores on
    [-1, 1] (``A_BT_score_full`` and ``D_BT_score_full``). Those two outputs
    are kept as the model emits them.
    """

    REPO_ID = "edsi-umd/PERT-EmoPair"
    BASE_MODEL = "roberta-large"

    PROMPT = (
        "- Valence: The emotional valence of the context is <mask>. "
        "- Arousal: The level of arousal of the context is <mask>. "
        "- Dominance: The perceived dominance associated with the context is <mask>. "
        "Please predict the missing value for each dimension using the content provided."
    )

    def __init__(
        self,
        device: str | None = None,
        max_length: int = 256,
    ):
        self.max_length = max_length

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = torch.device(device)

        print(f"Using device: {self.device}")

        # --------------------------------------------------
        # Tokenizer
        # --------------------------------------------------

        self.tokenizer = AutoTokenizer.from_pretrained(self.REPO_ID)

        # --------------------------------------------------
        # Model architecture
        # --------------------------------------------------

        self.model = RoBERTaForVAD(base_model_name=self.BASE_MODEL)

        # --------------------------------------------------
        # Download PERT-EmoPair checkpoint
        # --------------------------------------------------

        model_dir = snapshot_download(repo_id=self.REPO_ID)

        checkpoint_path = Path(model_dir) / "pytorch_model.bin"

        if not checkpoint_path.exists():
            raise FileNotFoundError(f"Checkpoint not found: {checkpoint_path}")

        # --------------------------------------------------
        # Load checkpoint
        # --------------------------------------------------

        checkpoint = torch.load(
            checkpoint_path,
            map_location="cpu",
            weights_only=True,
        )

        self.model.load_state_dict(checkpoint["model_state_dict"])

        # --------------------------------------------------
        # Evaluation mode
        # --------------------------------------------------

        self.model.to(self.device)
        self.model.eval()

        print("PERT-EmoPair loaded successfully.")

    def _build_prompt(self, text: str) -> str:
        return f"Context: '{text}' {self.PROMPT}"

    def _predict(self, text: str) -> list[float]:

        prompted_text = self._build_prompt(text)

        encoded = self.tokenizer(
            prompted_text,
            return_tensors="pt",
            truncation=True,
            max_length=self.max_length,
        )

        encoded = {key: value.to(self.device) for key, value in encoded.items()}

        with torch.inference_mode():
            output = self.model(**encoded)

        return output.squeeze(0).detach().cpu().tolist()

    def score(self, text: str) -> Score:
        result = Score()

        if not text or not text.strip():
            result.add_dimension_score(
                DimensionScore(
                    value=0.0,
                    kind=DimensionKind.VALENCE,
                )
            )
            result.add_dimension_score(
                DimensionScore(
                    value=0.0,
                    kind=DimensionKind.AROUSAL,
                )
            )
            result.add_dimension_score(
                DimensionScore(
                    value=0.0,
                    kind=DimensionKind.DOMINANCE,
                )
            )
            return result

        valence, arousal, dominance = self._predict(text)

        result.add_dimension_score(
            DimensionScore(
                value=emobank_to_bipolar(float(valence)),
                kind=DimensionKind.VALENCE,
            )
        )

        result.add_dimension_score(
            DimensionScore(
                value=float(arousal),
                kind=DimensionKind.AROUSAL,
            )
        )

        result.add_dimension_score(
            DimensionScore(
                value=float(dominance),
                kind=DimensionKind.DOMINANCE,
            )
        )

        return result

    @property
    def scorer_name(self) -> str:
        return "pert-emopair"

    @property
    def scorer_kind(self) -> ScorerKind:
        return ScorerKind.TRANSFORMER


# class RoBERTaForVAD(nn.Module):
#     """RoBERTa-large with a regression head for VAD prediction."""
#
#     def __init__(self, base_model_name: str) -> None:
#         super().__init__()
#
#         self.base_model = RobertaModel.from_pretrained(base_model_name)
#         self.dropout = nn.Dropout(p=0.1)
#         self.regressor = nn.Linear(
#             self.base_model.config.hidden_size,
#             3,
#         )
#
#     def forward(
#         self,
#         input_ids: Tensor,
#         attention_mask: Tensor,
#     ) -> Tensor:
#         outputs = self.base_model(
#             input_ids=input_ids,
#             attention_mask=attention_mask,
#         )
#
#         cls_embedding = self.dropout(outputs.last_hidden_state[:, 0, :])
#
#         return self.regressor(cls_embedding)

# class PERTEmoPairScorer(SentimentScorer):
#     """PERT-EmoPair based VAD scorer."""
#
#     @property
#     def scorer_name(self) -> str:
#         return "PERT-EmoPair"
#
#     @property
#     def scorer_kind(self) -> ScorerKind:
#         return ScorerKind.TRANSFORMER
#
#     _BASE_MODEL_NAME = "roberta-large"
#
#     _PROMPT = (
#         "- Valence: The emotional valence of the context is <mask>. "
#         "- Arousal: The level of arousal of the context is <mask>. "
#         "- Dominance: The perceived dominance associated with the context is <mask>. "
#         "Please predict the missing value for each dimension using the content provided."
#     )
#
#     _MAX_LENGTH = 256
#
#     def __init__(
#         self,
#         model_path: Path,
#         device: torch.device | None = None,
#     ) -> None:
#         self._device = device or self._default_device()
#
#         self._tokenizer = AutoTokenizer.from_pretrained(
#             self._BASE_MODEL_NAME,
#         )
#
#         self._model = RoBERTaForVAD(
#             self._BASE_MODEL_NAME,
#         )
#
#         self._load_weights(model_path)
#
#         self._model.to(self._device)
#         self._model.eval()
#
#     def score(self, text: str) -> Score:
#         """Return VAD scores for the given text."""
#
#         prompted_text = self._build_prompt(text)
#
#         inputs = self._tokenizer(
#             prompted_text,
#             return_tensors="pt",
#             truncation=True,
#             max_length=self._MAX_LENGTH,
#         )
#
#         input_ids = inputs["input_ids"].to(self._device)
#         attention_mask = inputs["attention_mask"].to(self._device)
#
#         with torch.inference_mode():
#             predictions = self._model(
#                 input_ids=input_ids,
#                 attention_mask=attention_mask,
#             )
#
#         return self._to_score(predictions.squeeze(0))
#
#     @classmethod
#     def _build_prompt(cls, text: str) -> str:
#         return f"Context: '{text}' {cls._PROMPT}"
#
#     def _load_weights(self, model_path: Path) -> None:
#         state = torch.load(
#             model_path,
#             map_location=self._device,
#             weights_only=True,
#         )
#
#         model_state_dict = state["model_state_dict"]
#
#         self._model.load_state_dict(model_state_dict)
#
#     @staticmethod
#     def _default_device() -> torch.device:
#         if torch.cuda.is_available():
#             return torch.device("cuda")
#
#         return torch.device("cpu")
#
#     @staticmethod
#     def _to_score(predictions: Tensor) -> Score:
#         valence = float(predictions[0].item())
#         arousal = float(predictions[1].item())
#         dominance = float(predictions[2].item())
#
#         score = Score()
#
#         score.add_dimension_score(
#             DimensionScore(
#                 value=PERTEmoPairScorer._normalize_valence(valence),
#                 kind=DimensionKind.VALENCE,
#             )
#         )
#
#         score.add_dimension_score(
#             DimensionScore(
#                 value=arousal,
#                 kind=DimensionKind.AROUSAL,
#             )
#         )
#
#         score.add_dimension_score(
#             DimensionScore(
#                 value=dominance,
#                 kind=DimensionKind.DOMINANCE,
#             )
#         )
#
#         return score
#
#     @staticmethod
#     def _normalize_valence(value: float) -> float:
#         """
#         Convert EmoBank valence from [1, 5] to [-1, 1].
#         """
#         return (value - 3.0) / 2.0
