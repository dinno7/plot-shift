"""DistilBERT SST-2 score mapping. These tests do not download the model."""

import pytest

pytest.importorskip("torch")
pytest.importorskip("transformers")

from plot_shift.sentiment.distilbert_sst2_scorer import class_index, signed_sst2_valence


def test_signed_valence_uses_probability_difference() -> None:
    assert signed_sst2_valence(negative=0.0, positive=1.0) == 1.0
    assert signed_sst2_valence(negative=1.0, positive=0.0) == -1.0
    assert signed_sst2_valence(negative=0.5, positive=0.5) == 0.0
    assert signed_sst2_valence(negative=0.2, positive=0.8) == pytest.approx(0.6)


def test_class_index_matches_label_name() -> None:
    id2label = {0: "NEGATIVE", 1: "POSITIVE"}

    assert class_index(id2label, "NEGATIVE") == 0
    assert class_index(id2label, "positive") == 1


def test_class_index_accepts_string_keys() -> None:
    id2label = {"0": "NEGATIVE", "1": "POSITIVE"}

    assert class_index(id2label, "POSITIVE") == 1


def test_class_index_rejects_unknown_label() -> None:
    with pytest.raises(ValueError, match="POSITIVE"):
        class_index({0: "LABEL_0", 1: "LABEL_1"}, "POSITIVE")
