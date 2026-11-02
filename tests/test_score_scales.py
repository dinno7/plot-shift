"""Fixed score scales. These tests do not load transformer weights."""

import pytest

from plot_shift.sentiment.base import DimensionKind
from plot_shift.sentiment.scales import emobank_to_bipolar
from plot_shift.sentiment.vad_scorer import VADLexiconScorer
from plot_shift.sentiment.vader_scorer import VaderLexiconScorer


def test_emobank_midpoint_and_ends() -> None:
    assert emobank_to_bipolar(1.0) == -1.0
    assert emobank_to_bipolar(3.0) == 0.0
    assert emobank_to_bipolar(5.0) == 1.0


def test_emobank_matches_emopair_rescaled_column() -> None:
    # EmoPair ``A_rescaled`` for an EmoBank arousal of 3.1 is 0.05.
    assert emobank_to_bipolar(3.1) == pytest.approx(0.05)
    assert emobank_to_bipolar(2.8) == pytest.approx(-0.1)


def test_vader_compound_stays_inside_unit_interval() -> None:
    scorer = VaderLexiconScorer()
    value = scorer.score("good").dimensions[0].value

    assert scorer.score("good").dimensions[0].kind is DimensionKind.VALENCE
    assert -1.0 < value < 1.0
    assert value == pytest.approx(0.4404, abs=1e-3)


def test_vad_compound_squashes_a_single_word(tmp_path) -> None:
    lexicon = tmp_path / "vad.txt"
    lexicon.write_text(
        "term\tvalence\tarousal\tdominance\ngood\t1.0\t0.5\t-0.2\n",
        encoding="utf-8",
    )
    scorer = VADLexiconScorer(lexicon)
    by_kind = {item.kind: item.value for item in scorer.score("good").dimensions}

    # normalize(1) = 1 / sqrt(1^2 + 1), rounded to 4 decimals by the analyzer.
    assert by_kind[DimensionKind.VALENCE] == pytest.approx(0.7071)
    assert by_kind[DimensionKind.AROUSAL] == pytest.approx(0.4472)
    assert by_kind[DimensionKind.DOMINANCE] == pytest.approx(-0.1961)
    assert all(-1.0 < value < 1.0 for value in by_kind.values())
