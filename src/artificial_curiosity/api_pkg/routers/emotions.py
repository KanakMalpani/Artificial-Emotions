"""Emotion catalog and epistemic cue annotations (UX annotations — not a CME).

Every path is registered twice: ``/v1/emotions/*`` and the ``/v1/epistemic/*``
alias, sharing one handler. The private ``_emotions_*`` helpers exist so the
GET and POST variants of the same operation cannot drift apart.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from artificial_curiosity.api_pkg.schemas import AnnotateEmotionsRequest, MixEmotionsRequest
from artificial_curiosity.emotions import (
    annotate_epistemic,
    elicit_helpers,
    emotion_catalog,
    emotion_pack,
    list_epistemic_cues,
    mix_emotions,
)

router = APIRouter()


def _emotions_cues() -> dict[str, Any]:
    return list_epistemic_cues()


def _emotions_catalog(family: str | None = None) -> dict[str, Any]:
    return emotion_catalog(family=family)


def _emotions_mix(req: MixEmotionsRequest) -> dict[str, Any]:
    return mix_emotions(
        req.weights,
        profile_name=req.profile_name,
        mix_intensity_cap=req.mix_intensity_cap,
        simulate_feeling=req.simulate_feeling,
    )


def _emotions_annotate(req: AnnotateEmotionsRequest) -> dict[str, Any]:
    return annotate_epistemic(
        req.question,
        gap_status=req.gap_status,
        surprise=req.surprise,
        neglectedness=req.neglectedness,
        answerability=req.answerability,
        notes=req.notes,
        domain=req.domain,
    )


def _emotions_elicit() -> dict[str, Any]:
    return elicit_helpers()


def _emotions_pack(name: str = "affective_science") -> dict[str, Any]:
    return emotion_pack(name)


@router.get("/v1/emotions/cues")
@router.get("/v1/epistemic/cues")
def emotions_cues() -> dict[str, Any]:
    """List epistemic cue tags (investigation framing — not felt emotion)."""
    return _emotions_cues()


@router.get("/v1/emotions/catalog")
@router.get("/v1/epistemic/catalog")
def emotions_catalog(
    family: str | None = Query(
        None,
        description="Optional filter: epistemic | basic | social | achievement",
    ),
) -> dict[str, Any]:
    """Named mixable emotion catalog (annotation only)."""
    return _emotions_catalog(family)


@router.post("/v1/emotions/mix")
@router.post("/v1/epistemic/mix")
def emotions_mix(req: MixEmotionsRequest) -> dict[str, Any]:
    """Mix catalog emotions by percent/weight; normalize to sum=1.0."""
    return _emotions_mix(req)


@router.post("/v1/emotions/annotate")
@router.post("/v1/epistemic/annotate")
def emotions_annotate(req: AnnotateEmotionsRequest) -> dict[str, Any]:
    """Annotate question text with epistemic cue tags."""
    return _emotions_annotate(req)


@router.get("/v1/emotions/annotate")
@router.get("/v1/epistemic/annotate")
def emotions_annotate_get(
    question: str = Query(..., min_length=12),
    gap_status: str = Query("unanswered"),
    surprise: float = Query(0.5, ge=0.0, le=1.0),
    neglectedness: float = Query(0.5, ge=0.0, le=1.0),
    answerability: float = Query(0.5, ge=0.0, le=1.0),
    notes: str = Query(""),
    domain: str = Query("ai"),
) -> dict[str, Any]:
    """GET annotate for curl / browsers."""
    return _emotions_annotate(
        AnnotateEmotionsRequest(
            question=question,
            gap_status=gap_status,
            surprise=surprise,
            neglectedness=neglectedness,
            answerability=answerability,
            notes=notes,
            domain=domain,
        )
    )


@router.get("/v1/emotions/elicit")
@router.get("/v1/epistemic/elicit")
def emotions_elicit() -> dict[str, Any]:
    """Incongruity → investigation framing + inject helpers."""
    return _emotions_elicit()


@router.get("/v1/emotions/pack")
@router.get("/v1/epistemic/pack")
def emotions_pack(
    name: str = Query("affective_science", description="Bundled pack id"),
) -> dict[str, Any]:
    """Affective-science (or named) domain pack — ranking seeds, not an emotion engine."""
    return _emotions_pack(name)
