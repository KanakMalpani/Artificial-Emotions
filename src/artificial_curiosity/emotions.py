"""Public emotion / epistemic-cue surface (UX annotations only).

These helpers expose *epistemic* tags for investigation framing
(incongruity, information-gap, confusion-risk, …). They are NOT a
computational emotion model and do NOT claim the system feels anything.

See docs/EMOTIONS.md and research/AI_EMOTIONS.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from artificial_curiosity.epistemic_cues import (
    EPISTEMIC_CUE_DISCLAIMER,
    TAG_BOREDOM_GUARD,
    TAG_CONFUSION_RISK,
    TAG_CURIOSITY_TARGET,
    TAG_INFORMATION_GAP,
    TAG_INCONGRUITY,
    TAG_SURPRISE_SIGNAL,
    derive_epistemic_cues,
    format_cues_for_inject,
    incongruity_investigate_block,
)
from artificial_curiosity.models import (
    GapEvidence,
    GapStatus,
    RankedQuestion,
    ScoreAxes,
    UnansweredQuestion,
)
from artificial_curiosity.packs import load_pack_file, questions_from_pack

# Re-export stable vocabulary for `from artificial_curiosity.emotions import …`
__all__ = [
    "EPISTEMIC_CUE_DISCLAIMER",
    "CUE_CATALOG",
    "list_epistemic_cues",
    "annotate_epistemic",
    "elicit_helpers",
    "emotion_pack",
    "derive_epistemic_cues",
    "format_cues_for_inject",
    "incongruity_investigate_block",
    "TAG_INCONGRUITY",
    "TAG_INFORMATION_GAP",
    "TAG_CURIOSITY_TARGET",
    "TAG_CONFUSION_RISK",
    "TAG_SURPRISE_SIGNAL",
    "TAG_BOREDOM_GUARD",
]

CUE_CATALOG: list[dict[str, str]] = [
    {
        "tag": TAG_INFORMATION_GAP,
        "meaning": "Gap looks unanswered / partially answered — knowledge missing.",
    },
    {
        "tag": TAG_CURIOSITY_TARGET,
        "meaning": "Item is a candidate investigation target (functional curiosity cue).",
    },
    {
        "tag": TAG_CONFUSION_RISK,
        "meaning": "Partial/caveated gap or low answerability — risk of stuck confusion.",
    },
    {
        "tag": TAG_SURPRISE_SIGNAL,
        "meaning": "High surprise axis with an open gap — unexpectedness signal.",
    },
    {
        "tag": TAG_INCONGRUITY,
        "meaning": "Related literature ≠ answered, or surprise+gap — incongruity framing.",
    },
    {
        "tag": TAG_BOREDOM_GUARD,
        "meaning": "High neglectedness — prefer under-explored over over-covered topics.",
    },
]

_AFFECTIVE_PACK = "affective_science.json"


def list_epistemic_cues() -> dict[str, Any]:
    """List stable cue tags + honesty disclaimer (offline-safe)."""
    return {
        "cues": list(CUE_CATALOG),
        "tags": [c["tag"] for c in CUE_CATALOG],
        "honesty": "annotation_only",
        "disclaimer": EPISTEMIC_CUE_DISCLAIMER,
        "docs": "docs/EMOTIONS.md",
        "note": (
            "Epistemic cues annotate investigation framing. "
            "This software does not feel emotions."
        ),
    }


def _parse_gap_status(raw: str | GapStatus | None) -> GapStatus:
    if raw is None:
        return GapStatus.UNANSWERED
    if isinstance(raw, GapStatus):
        return raw
    key = str(raw).strip().lower()
    try:
        return GapStatus(key)
    except ValueError as exc:
        known = ", ".join(s.value for s in GapStatus)
        raise ValueError(f"Unknown gap_status '{raw}'. Known: {known}") from exc


def annotate_epistemic(
    question: str,
    *,
    gap_status: str | GapStatus = "unanswered",
    surprise: float = 0.5,
    neglectedness: float = 0.5,
    answerability: float = 0.5,
    notes: str = "",
    domain: str = "ai",
    operationalization: str = "Specify a falsifiable first experiment or analysis.",
    why_it_matters: str = "Annotate epistemic framing for an investigation candidate.",
) -> dict[str, Any]:
    """Annotate free-text (or scores) with epistemic cue tags.

    Offline-safe heuristics — same vocabulary as provoke inject packs.
    """
    q = (question or "").strip()
    if len(q) < 12:
        raise ValueError("question too short (need ≥12 characters)")

    def _clamp(x: float) -> float:
        return max(0.0, min(1.0, float(x)))

    item = RankedQuestion(
        question=UnansweredQuestion(
            id="annotate-ephemeral",
            question=q,
            domain=domain,
            operationalization=operationalization,
            why_it_matters=why_it_matters,
        ),
        scores=ScoreAxes(
            impact=0.5,
            neglectedness=_clamp(neglectedness),
            tractability=0.5,
            surprise=_clamp(surprise),
            answerability=_clamp(answerability),
            risk=0.2,
            cost_proxy=0.4,
        ),
        curiosity_score=0.5,
        confidence=0.4,
        gap=GapEvidence(
            status=_parse_gap_status(gap_status),
            confidence=0.5,
            notes=notes or "",
        ),
        rank=1,
    )
    cues = derive_epistemic_cues(item)
    return {
        "question": q,
        "gap_status": item.gap.status.value,
        "axes": {
            "surprise": item.scores.surprise,
            "neglectedness": item.scores.neglectedness,
            "answerability": item.scores.answerability,
        },
        "epistemic_cues": cues,
        "inject_fragment": format_cues_for_inject(cues),
        "honesty": "annotation_only",
        "disclaimer": EPISTEMIC_CUE_DISCLAIMER,
    }


def elicit_helpers() -> dict[str, Any]:
    """Elicit / inject helpers for incongruity → investigation framing."""
    framing = incongruity_investigate_block()
    return {
        "framing": framing,
        "inject_prefix": (
            "Epistemic framing (not anthropomorphism): treat ranked items as "
            "information gaps / incongruities. Name missing knowledge → first "
            "experiment → falsifier. This layer does not feel."
        ),
        "how_to_use": [
            "Call list_epistemic_cues (or GET /v1/emotions/cues) for the tag vocabulary.",
            "Annotate a draft question with annotate_epistemic (or POST /v1/emotions/annotate).",
            "Paste framing + inject_fragment into agent context alongside provoke inject packs.",
        ],
        "disclaimer": EPISTEMIC_CUE_DISCLAIMER,
        "honesty": "annotation_only",
        "docs": "docs/EMOTIONS.md",
    }


def emotion_pack(name: str = "affective_science") -> dict[str, Any]:
    """Load a bundled domain pack useful for affective / epistemic research.

    Default: ``affective_science`` — ranking seeds only, not an emotion engine.
    """
    key = (name or "affective_science").strip().lower().replace("-", "_")
    if key in ("affective_science", "affective_science_pack", "affect"):
        filename = _AFFECTIVE_PACK
        pack_key = "affective_science"
    else:
        raise ValueError(
            f"Unknown emotion pack '{name}'. Available: affective_science"
        )

    path = Path(__file__).resolve().parent / "packs" / filename
    data = load_pack_file(path)
    qs = questions_from_pack(data)
    return {
        "name": pack_key,
        "pack_name": data.get("name"),
        "version": data.get("version"),
        "domain": data.get("domain"),
        "description": data.get("description"),
        "count": len(qs),
        "questions": [
            {
                "id": q.id,
                "question": q.question,
                "operationalization": q.operationalization,
                "why_it_matters": q.why_it_matters,
                "tags": q.tags,
                "assumptions": q.assumptions,
            }
            for q in qs
        ],
        "honesty": "annotation_only",
        "disclaimer": (
            "Domain pack seeds for ranking / evals — not a CME or claim that "
            "the system feels emotions. " + EPISTEMIC_CUE_DISCLAIMER
        ),
        "docs": "docs/EMOTIONS.md",
        "research": "research/AI_EMOTIONS.md",
    }
