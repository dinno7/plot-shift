"""Jev scorer tests. The client is fake, so these do not call the API."""

from collections.abc import Mapping

import pytest
from typesafe_sdk.constants import DEFAULT_BASE_URL, DEFAULT_TIMEOUT

from plot_shift.sentiment.base import DimensionKind
from plot_shift.sentiment.jev_scorer import (
    JEV_MODEL,
    JevScorer,
    jev_client_settings,
    scale_jev_score,
)

_JSON_HEADERS = {"Content-Type": "application/json", "Accept": "application/json"}


class _Answer:
    def __init__(self, score: float) -> None:
        self.score = score


class _Response:
    def __init__(self, scores: dict[str, float]) -> None:
        self.scores = {name: _Answer(score) for name, score in scores.items()}


class _FakeClient:
    def __init__(self, scores: dict[str, float]) -> None:
        self.scores = scores
        self.states: list[Mapping[str, str]] = []
        self.questions: list[Mapping[str, object]] = []

    def system_one(self, *, state: Mapping[str, str], questions: Mapping[str, object]) -> _Response:
        self.states.append(state)
        self.questions.append(questions)
        return _Response(self.scores)


def test_client_settings_use_defaults() -> None:
    settings = jev_client_settings(environ={})

    assert settings == {
        "model": JEV_MODEL,
        "base_url": DEFAULT_BASE_URL,
        "compression": False,
        "timeout": DEFAULT_TIMEOUT,
        "headers": _JSON_HEADERS,
    }


def test_client_settings_read_environment() -> None:
    settings = jev_client_settings(
        environ={
            "TYPESAFE_DEFAULT_MODEL": "local-jev",
            "TYPESAFE_BASE_URL": "http://127.0.0.1:8080",
            "TYPESAFE_TIMEOUT": "30",
        }
    )

    assert settings == {
        "model": "local-jev",
        "base_url": "http://127.0.0.1:8080",
        "compression": False,
        "timeout": 30.0,
        "headers": _JSON_HEADERS,
    }


def test_explicit_model_overrides_environment() -> None:
    settings = jev_client_settings(
        model="jev-1.13.0", environ={"TYPESAFE_DEFAULT_MODEL": "local-jev"}
    )

    assert settings["model"] == "jev-1.13.0"


def test_timeout_must_be_positive() -> None:
    with pytest.raises(ValueError, match="TYPESAFE_TIMEOUT"):
        jev_client_settings(environ={"TYPESAFE_TIMEOUT": "0"})


def test_scale_jev_score_maps_ends_and_middle() -> None:
    assert scale_jev_score(0.0, top_level=4) == -1.0
    assert scale_jev_score(2.0, top_level=4) == 0.0
    assert scale_jev_score(4.0, top_level=4) == 1.0


def test_score_maps_valence() -> None:
    client = _FakeClient({"valence": 0.0})
    scorer = JevScorer(client=client)

    score = scorer.score("The ship sinks. Then they laugh.")

    assert scorer.scorer_name == "jev"
    assert [dimension.kind for dimension in score.dimensions] == [DimensionKind.VALENCE]
    assert [dimension.value for dimension in score.dimensions] == [-1.0]
    assert client.states == [{"subtitles": "The ship sinks. Then they laugh."}]
    assert [set(questions) for questions in client.questions] == [{"valence"}]


def test_blank_text_skips_the_api() -> None:
    client = _FakeClient({"valence": 4.0})
    scorer = JevScorer(client=client)

    score = scorer.score("   ")

    assert [dimension.kind for dimension in score.dimensions] == [DimensionKind.VALENCE]
    assert [dimension.value for dimension in score.dimensions] == [0.0]
    assert client.states == []
