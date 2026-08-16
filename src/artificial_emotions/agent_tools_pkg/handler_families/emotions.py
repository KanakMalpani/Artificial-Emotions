"""Affect-family tools: epistemic cues, packs, catalog, mix."""

from __future__ import annotations

from typing import Any

from artificial_emotions.emotions import (
    annotate_epistemic,
    elicit_helpers,
    emotion_catalog,
    emotion_pack,
    list_epistemic_cues,
    mix_emotions,
)

__all__ = [
    "handle_annotate_epistemic",
    "handle_elicit_helpers",
    "handle_emotion_catalog",
    "handle_emotion_pack",
    "handle_list_epistemic_cues",
    "handle_mix_emotions",
]


def handle_list_epistemic_cues(**_extra: Any) -> dict[str, Any]:
    """List epistemic cue tag vocabulary (UX annotations — not felt emotion)."""
    return list_epistemic_cues()


def handle_annotate_epistemic(
    *,
    question: str,
    gap_status: str = "unanswered",
    surprise: float = 0.5,
    neglectedness: float = 0.5,
    answerability: float = 0.5,
    notes: str = "",
    domain: str = "ai",
    **_extra: Any,
) -> dict[str, Any]:
    """Annotate question text with epistemic cue tags."""
    return annotate_epistemic(
        question,
        gap_status=gap_status,
        surprise=float(surprise),
        neglectedness=float(neglectedness),
        answerability=float(answerability),
        notes=notes or "",
        domain=domain,
    )


def handle_emotion_pack(
    *,
    name: str = "affective_science",
    **_extra: Any,
) -> dict[str, Any]:
    """Return affective_science (or named) domain pack seeds."""
    return emotion_pack(name or "affective_science")


def handle_elicit_helpers(**_extra: Any) -> dict[str, Any]:
    """Incongruity → investigation framing + inject helpers."""
    return elicit_helpers()


def handle_emotion_catalog(
    *,
    family: str | None = None,
    **_extra: Any,
) -> dict[str, Any]:
    """Return mixable named-emotion catalog (computational affect simulation)."""
    return emotion_catalog(family=family or None)


def handle_mix_emotions(
    *,
    weights: dict[str, Any] | None = None,
    profile_name: str | None = None,
    mix_intensity_cap: float | None = None,
    simulate_feeling: bool = True,
    **_extra: Any,
) -> dict[str, Any]:
    """Mix catalog emotions by percent/weight; normalize to sum=1.0."""
    if not isinstance(weights, dict) or not weights:
        raise ValueError(
            'weights must be a non-empty object, e.g. {"curiosity": 40, "confusion": 30, "awe": 30}'
        )
    cleaned: dict[str, float] = {}
    for key, val in weights.items():
        cleaned[str(key)] = float(val)
    return mix_emotions(
        cleaned,
        profile_name=profile_name,
        mix_intensity_cap=mix_intensity_cap,
        simulate_feeling=simulate_feeling,
    )
