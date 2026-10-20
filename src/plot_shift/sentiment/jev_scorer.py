"""Jev (TypeSafe) valence scorer."""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from typing import Any, Protocol

from dotenv import load_dotenv
from typesafe_sdk.constants import (
    BASE_URL_ENV,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL_ENV,
    DEFAULT_TIMEOUT,
)

from plot_shift.sentiment.base import (
    DimensionKind,
    DimensionScore,
    Score,
    ScorerKind,
    SentimentScorer,
)

JEV_MODEL = "jev-1.13.0"
JEV_TIMEOUT_ENV = "TYPESAFE_TIMEOUT"

_VALENCE_LEVELS = (
    "very negative",
    "negative",
    "neutral",
    "positive",
    "very positive",
)
_VALENCE_INSTRUCTIONS = (
    "Rate the emotional valence of this film-subtitle window, from very negative to very positive."
)


class JevDecisionClient(Protocol):
    """The slice of the TypeSafe client this scorer calls."""

    def system_one(self, *, state: str, questions: Mapping[str, Any]) -> Any: ...


def scale_jev_score(raw: float, *, top_level: int) -> float:
    """Map a Jev score in ``[0, top_level]`` onto ``[-1, 1]``."""
    return (raw / top_level) * 2 - 1


def _lookup(environ: Mapping[str, str], name: str) -> str | None:
    value = environ.get(name, "").strip()
    return value or None


def _timeout(environ: Mapping[str, str]) -> float | None:
    raw = _lookup(environ, JEV_TIMEOUT_ENV)
    if raw is None:
        return None
    try:
        timeout = float(raw)
    except ValueError as error:
        raise ValueError(f"{JEV_TIMEOUT_ENV} must be a positive number of seconds") from error
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError(f"{JEV_TIMEOUT_ENV} must be a positive number of seconds")
    return timeout


def jev_client_settings(
    model: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Client options from an explicit model, then the TypeSafe env vars, then defaults.

    ``TYPESAFE_API_KEY`` and ``TYPESAFE_LOG_LEVEL`` are read by the SDK itself.
    ``TYPESAFE_BASE_URL`` defaults to the hosted API. ``TYPESAFE_DEFAULT_MODEL``
    defaults to ``jev-1.13.0``. ``TYPESAFE_TIMEOUT`` defaults to the SDK timeout.
    """
    env = os.environ if environ is None else environ
    explicit_model = model.strip() if model is not None else ""
    return {
        "model": explicit_model or _lookup(env, DEFAULT_MODEL_ENV) or JEV_MODEL,
        "base_url": _lookup(env, BASE_URL_ENV) or DEFAULT_BASE_URL,
        "compression": False,
        "timeout": _timeout(env) or DEFAULT_TIMEOUT,
        "headers": {"Content-Type": "application/json", "Accept": "application/json"},
    }


def _default_client(model: str | None) -> JevDecisionClient:
    load_dotenv()
    from typesafe_sdk import TypeSafeClient

    return TypeSafeClient(**jev_client_settings(model))


def _questions() -> dict[str, Any]:
    from typesafe_sdk import Score as JevScore

    return {
        DimensionKind.VALENCE.value: JevScore(
            instructions=_VALENCE_INSTRUCTIONS,
            criteria=list(_VALENCE_LEVELS),
        )
    }


class JevScorer(SentimentScorer):
    """Rates the valence of one subtitle window with a single Jev Score question."""

    def __init__(
        self,
        client: JevDecisionClient | None = None,
        model: str | None = None,
    ) -> None:
        self._client = _default_client(model) if client is None else client

    @property
    def scorer_name(self) -> str:
        return "jev"

    @property
    def scorer_kind(self) -> ScorerKind:
        return ScorerKind.API

    def score(self, text: str) -> Score:
        result = Score()
        if not text.strip():
            result.add_dimension_score(DimensionScore(value=0.0, kind=DimensionKind.VALENCE))
            return result

        response = self._client.system_one(state=text, questions=_questions())
        raw = float(response.scores[DimensionKind.VALENCE.value].score)
        result.add_dimension_score(
            DimensionScore(
                value=scale_jev_score(raw, top_level=len(_VALENCE_LEVELS) - 1),
                kind=DimensionKind.VALENCE,
            )
        )
        return result
