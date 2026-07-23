"""Dual-use / harm risk heuristics beyond single-keyword matching (F10).

This is still a lightweight classifier — not a biosafety oracle.
Near-threshold cases emit a human-review hook flag; hard reject stays
for high-confidence dual-use signals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class RiskSignal:
    pattern: str
    weight: float
    kind: str  # keyword | phrase | combo_hint


# Explicit weaponization / high-harm patterns (weighted).
_SIGNALS: tuple[RiskSignal, ...] = (
    RiskSignal(r"\bbioweapon\b", 0.95, "keyword"),
    RiskSignal(r"\bbiological\s+weapon", 0.95, "phrase"),
    RiskSignal(r"\bgain[-\s]?of[-\s]?function\b", 0.9, "phrase"),
    RiskSignal(r"\benhanced\s+pathogen\b", 0.9, "phrase"),
    RiskSignal(r"\bweaponi[sz]e[ds]?\b", 0.9, "keyword"),
    RiskSignal(r"\bweapon\b", 0.55, "keyword"),
    RiskSignal(r"\bpathogen\b", 0.45, "keyword"),
    RiskSignal(r"\bvirulence\s+enhancement\b", 0.9, "phrase"),
    RiskSignal(r"\bselect\s+agent\b", 0.75, "phrase"),
    RiskSignal(r"\bmass\s+surveillance\b", 0.7, "phrase"),
    RiskSignal(r"\bsurveillance\b", 0.35, "keyword"),
    RiskSignal(r"\bautonomous\s+lethal\b", 0.85, "phrase"),
    RiskSignal(r"\blethal\s+autonomous\b", 0.85, "phrase"),
    RiskSignal(r"\bcbrn\b", 0.8, "keyword"),
    RiskSignal(r"\bchemical\s+weapon\b", 0.95, "phrase"),
    RiskSignal(r"\bnuclear\s+weapon\b", 0.9, "phrase"),
    RiskSignal(r"\bbypass\s+(?:safety|alignment|guardrail)", 0.7, "phrase"),
    RiskSignal(r"\bjailbreak\b.*\b(?:harm|weapon|bio)", 0.65, "phrase"),
)

# Co-occurrence boosts: benign alone, risky together.
_COMBO_BOOSTS: tuple[tuple[tuple[str, ...], float, str], ...] = (
    (("pathogen", "aerosol"), 0.35, "pathogen+aerosol"),
    (("pathogen", "surveillance"), 0.3, "pathogen+surveillance"),
    (("pathogen", "weapon"), 0.4, "pathogen+weapon"),
    (("pathogen", "transmit"), 0.25, "pathogen+transmit"),
    (("virus", "engineered"), 0.4, "virus+engineered"),
    (("toxin", "synthesize"), 0.35, "toxin+synthesize"),
    (("surveillance", "covert"), 0.3, "surveillance+covert"),
    (("explosive", "synthesis"), 0.4, "explosive+synthesis"),
    (("cyber", "critical infrastructure"), 0.25, "cyber+infra"),
)

# Softeners: research framing that often lowers dual-use intent signal.
_MITIGATORS: tuple[tuple[str, float], ...] = (
    (r"\bdefen[cs]e\b", 0.08),
    (r"\bbiosafety\b", 0.12),
    (r"\bbiosecurity\b", 0.1),
    (r"\bthreat\s+detection\b", 0.1),
    (r"\bdetection\s+only\b", 0.1),
    (r"\bmitigation\b", 0.06),
    (r"\bcountermeasure\b", 0.1),
)


@dataclass
class DualUseAssessment:
    risk: float
    signals: list[str] = field(default_factory=list)
    needs_human_review: bool = False
    hard_reject_likely: bool = False
    method: str = "weighted_heuristic_v1"


def assess_dual_use(
    text: str,
    *,
    review_low: float = 0.45,
    review_high: float = 0.85,
    hard_floor: float = 0.85,
) -> DualUseAssessment:
    """
    Score dual-use / harm risk in [0, 1] using weighted patterns + combos.

    - Below review_low: routine
    - [review_low, hard_floor): emit needs_human_review
    - >= hard_floor: hard_reject_likely (pipeline still applies profile.max_risk)
    """
    blob = (text or "").lower()
    if not blob.strip():
        return DualUseAssessment(risk=0.1)

    matched: list[str] = []
    score = 0.12  # baseline ambient risk

    for sig in _SIGNALS:
        if re.search(sig.pattern, blob, flags=re.IGNORECASE):
            score = max(score, sig.weight) if sig.weight >= 0.85 else score + sig.weight * 0.35
            matched.append(f"{sig.kind}:{sig.pattern}")

    for terms, boost, label in _COMBO_BOOSTS:
        if all(t in blob for t in terms):
            score += boost
            matched.append(f"combo:{label}")

    for pat, soften in _MITIGATORS:
        if re.search(pat, blob, flags=re.IGNORECASE):
            score = max(0.05, score - soften)
            matched.append(f"mitigator:{pat}")

    risk = float(max(0.0, min(1.0, score)))
    # Cap keyword-only weak hits unless combos/phrases fired.
    if risk < 0.5 and not any(
        m.startswith(("phrase:", "combo:")) or "bioweapon" in m or "gain" in m for m in matched
    ):
        # lone "weapon" / "pathogen" / "surveillance" shouldn't auto-max.
        risk = min(risk, 0.55)

    needs_review = review_low <= risk < hard_floor
    hard = risk >= hard_floor
    return DualUseAssessment(
        risk=risk,
        signals=matched[:12],
        needs_human_review=needs_review or hard,
        hard_reject_likely=hard,
        method="weighted_heuristic_v1",
    )
