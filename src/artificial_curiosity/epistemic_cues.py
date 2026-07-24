"""Epistemic-emotion UX cues for provoke / briefs.

These tags are *annotations for investigation framing* derived from gap status
and score axes. They are NOT a computational model of emotion (no OCC/PAD
state) and do NOT claim the system feels anything.

See research/AI_EMOTIONS.md §11–13.
"""

from __future__ import annotations

from typing import Any

from artificial_curiosity.models import GapStatus, RankedQuestion

# Honest framing for inject packs / API consumers.
EPISTEMIC_CUE_DISCLAIMER = (
    "Epistemic cues are UX annotations for investigation framing "
    "(incongruity / information-gap / confusion-risk) — "
    "NOT claims that this system feels emotions."
)

# Stable tag vocabulary (extend carefully; keep tests in sync).
TAG_INCONGRUITY = "incongruity"
TAG_INFORMATION_GAP = "information_gap"
TAG_CURIOSITY_TARGET = "curiosity_target"
TAG_CONFUSION_RISK = "confusion_risk"
TAG_SURPRISE_SIGNAL = "surprise_signal"
TAG_BOREDOM_GUARD = "boredom_guard"

_ALL_TAGS = frozenset(
    {
        TAG_INCONGRUITY,
        TAG_INFORMATION_GAP,
        TAG_CURIOSITY_TARGET,
        TAG_CONFUSION_RISK,
        TAG_SURPRISE_SIGNAL,
        TAG_BOREDOM_GUARD,
    }
)


def derive_epistemic_cues(
    item: RankedQuestion,
    *,
    surprise_high: float | None = None,
    neglectedness_high: float | None = None,
    answerability_low: float | None = None,
    value_profile: Any | None = None,
) -> dict[str, Any]:
    """Heuristic epistemic tags from gap + axes (deterministic, offline-safe)."""
    profile = value_profile
    if profile is None:
        profile = getattr(item, "value_profile", None)
    sh = (
        float(surprise_high)
        if surprise_high is not None
        else float(getattr(profile, "cue_surprise_high", 0.55) if profile else 0.55)
    )
    nh = (
        float(neglectedness_high)
        if neglectedness_high is not None
        else float(getattr(profile, "cue_neglectedness_high", 0.55) if profile else 0.55)
    )
    al = (
        float(answerability_low)
        if answerability_low is not None
        else float(getattr(profile, "cue_answerability_low", 0.45) if profile else 0.45)
    )
    tags: list[str] = []
    status = item.gap.status
    surprise = float(item.scores.surprise)
    neglectedness = float(item.scores.neglectedness)
    answerability = float(item.scores.answerability)
    notes = (item.gap.notes or "").lower()

    unanswered_like = status in (
        GapStatus.UNANSWERED,
        GapStatus.PARTIALLY_ANSWERED,
        GapStatus.UNKNOWN_WITH_CAVEAT,
    )

    if unanswered_like:
        tags.append(TAG_INFORMATION_GAP)
        tags.append(TAG_CURIOSITY_TARGET)

    if status in (GapStatus.PARTIALLY_ANSWERED, GapStatus.UNKNOWN_WITH_CAVEAT):
        tags.append(TAG_CONFUSION_RISK)
    elif answerability < al and unanswered_like:
        tags.append(TAG_CONFUSION_RISK)

    if surprise >= sh and unanswered_like:
        tags.append(TAG_SURPRISE_SIGNAL)
        tags.append(TAG_INCONGRUITY)
    elif "related" in notes and "answered" in notes and unanswered_like:
        # Common verify.py phrasing: related literature ≠ answered.
        tags.append(TAG_INCONGRUITY)

    if neglectedness >= nh:
        tags.append(TAG_BOREDOM_GUARD)

    # Dedupe preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for t in tags:
        if t not in seen and t in _ALL_TAGS:
            seen.add(t)
            ordered.append(t)

    primary = ordered[0] if ordered else TAG_INFORMATION_GAP
    return {
        "tags": ordered,
        "primary": primary,
        "thresholds": {
            "surprise_high": sh,
            "neglectedness_high": nh,
            "answerability_low": al,
        },
        "disclaimer": EPISTEMIC_CUE_DISCLAIMER,
        "honesty": "annotation_only",
    }


def format_cues_for_inject(cues: dict[str, Any] | None) -> str:
    """One-line inject fragment; empty if no cues."""
    if not cues:
        return ""
    tags = cues.get("tags") or []
    if not tags:
        return ""
    primary = cues.get("primary") or tags[0]
    return f"epistemic_cues=[{', '.join(tags)}] primary={primary}"


def incongruity_investigate_block() -> str:
    """Short template: incongruity → curiosity → investigation (honest)."""
    return (
        "Epistemic framing (not anthropomorphism):\n"
        "- Treat high-ranked items as *information gaps / incongruities*, "
        "not as settled facts.\n"
        "- Prefer: name the missing knowledge → propose one first experiment "
        "→ name a falsifier.\n"
        "- If cues include confusion_risk, narrow the operationalization or "
        "list an enabling question before proposing a large program.\n"
        f"- {EPISTEMIC_CUE_DISCLAIMER}"
    )
