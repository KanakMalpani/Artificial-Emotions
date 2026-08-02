"""A6 Avoidance detection — persistent non-selection, pattern only.

Derived from PersistentMemory encounters vs selections. Flags questions seen
many times and picked zero times. Reports the pattern; explicitly cannot tell
avoidance from judgment. Does not claim motive or phenomenal feeling.

Phase-1 demo surface: ``emotions memory avoiding`` and explore closing monologue.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "CANNOT_DISTINGUISH_NOTE",
    "MIN_ENCOUNTERS_FOR_AVOIDANCE",
    "AvoidancePattern",
    "apply_avoidance_to_feeling",
    "avoidance_claims_not",
    "avoidance_monologue",
    "avoiding_payload",
    "detect_avoidance",
]

#: Real threshold — one sighting must never cry wolf (PLAN_ALIVE A6 / demo "six").
MIN_ENCOUNTERS_FOR_AVOIDANCE = 6

#: Honest limit: pattern ≠ motive. Required in every avoidance surface.
CANNOT_DISTINGUISH_NOTE = (
    "That pattern is either good judgment or avoidance, and I can't tell which from here."
)

_MOTIVE_CLAIM_PHRASES = (
    "i am avoiding",
    "i avoid because",
    "motivated by avoidance",
    "fear of",
    "i feel reluctant",
    "phenomenal",
)


@dataclass(frozen=True)
class AvoidancePattern:
    """One question with repeated encounters and zero selections."""

    question_id: str
    encounters: int
    selections: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "encounters": int(self.encounters),
            "selections": int(self.selections),
            "pattern": "seen_many_picked_zero",
            "cannot_distinguish": CANNOT_DISTINGUISH_NOTE,
            "claims_not": list(avoidance_claims_not()),
        }


def avoidance_claims_not() -> tuple[str, ...]:
    """Honesty tokens every avoidance surface must carry."""
    return (
        "a motive or psychological cause for non-selection",
        "that non-selection is avoidance rather than judgment",
        "phenomenal feeling or lived reluctance",
        "biological emotion",
    )


def detect_avoidance(
    encounters: dict[str, int],
    selections: dict[str, int] | None = None,
    *,
    min_encounters: int = MIN_ENCOUNTERS_FOR_AVOIDANCE,
) -> list[AvoidancePattern]:
    """Flag persistent non-selection. Requires real repeated encounters.

    A question is flagged only when ``encounters >= min_encounters`` and
    ``selections == 0``. One (or few) sightings never qualify.
    """
    floor = max(2, int(min_encounters))  # never allow a one-sighting threshold
    picked = selections or {}
    found: list[AvoidancePattern] = []
    for qid, count in (encounters or {}).items():
        n_seen = int(count)
        n_picked = int(picked.get(qid, 0))
        if n_seen >= floor and n_picked == 0:
            found.append(
                AvoidancePattern(
                    question_id=str(qid),
                    encounters=n_seen,
                    selections=n_picked,
                )
            )
    found.sort(key=lambda p: (-p.encounters, p.question_id))
    return found


def avoidance_monologue(patterns: list[AvoidancePattern]) -> str:
    """Closing text: countable pattern + explicit non-motive disclaimer."""
    if not patterns:
        return ""
    lines: list[str] = []
    for p in patterns:
        lines.append(
            f"I've now seen {p.question_id} in {p.encounters} sessions "
            f"and picked it up {p.selections} times. "
            f"Each time something scored marginally higher. "
            f"{CANNOT_DISTINGUISH_NOTE}"
        )
    return " ".join(lines)


def apply_avoidance_to_feeling(
    feeling: dict[str, Any] | None,
    patterns: list[AvoidancePattern],
) -> dict[str, Any] | None:
    """Append avoidance notice to ``inner_monologue``; never claim motive."""
    if feeling is None or not patterns:
        return feeling
    mono = avoidance_monologue(patterns)
    if not mono:
        return feeling
    out = dict(feeling)
    existing = str(out.get("inner_monologue") or "").rstrip()
    out["inner_monologue"] = f"{existing} {mono}".strip() if existing else mono
    out["avoiding"] = [p.to_dict() for p in patterns]
    not_claimed = list(out.get("not_claimed") or [])
    for token in avoidance_claims_not():
        if token not in not_claimed:
            not_claimed.append(token)
    out["not_claimed"] = not_claimed
    # Guard: monologue must not smuggle motive language.
    lowered = out["inner_monologue"].lower()
    for phrase in _MOTIVE_CLAIM_PHRASES:
        if phrase in lowered:
            # Strip accidental motive claims; keep the pattern sentence.
            out["inner_monologue"] = mono
            break
    return out


def avoiding_payload(
    *,
    encounters: dict[str, int],
    selections: dict[str, int] | None = None,
    min_encounters: int = MIN_ENCOUNTERS_FOR_AVOIDANCE,
) -> dict[str, Any]:
    """CLI / JSON surface for ``emotions memory avoiding``."""
    patterns = detect_avoidance(
        encounters,
        selections,
        min_encounters=min_encounters,
    )
    return {
        "avoiding": [p.to_dict() for p in patterns],
        "count": len(patterns),
        "min_encounters": max(2, int(min_encounters)),
        "monologue": avoidance_monologue(patterns),
        "honesty": "pattern_not_motive",
        "claims_not": list(avoidance_claims_not()),
        "cannot_distinguish": CANNOT_DISTINGUISH_NOTE,
        "note": (
            "Persistent non-selection from local memory encounters vs selections. "
            "Annotation only — does not feel; cannot distinguish avoidance from judgment."
        ),
    }
