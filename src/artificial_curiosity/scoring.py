"""Multi-axis curiosity scoring with uncertainty."""

from __future__ import annotations

import math
import statistics

from artificial_curiosity.models import (
    GapStatus,
    ScoreAxes,
    UnansweredQuestion,
    ValueProfile,
)


def aggregate_curiosity(
    axes: ScoreAxes,
    profile: ValueProfile,
    eps: float = 1e-3,
) -> float:
    """
    curiosity = (I^α N^β T^γ S^δ) * A * (1-R) / (cost + eps)

    Geometric mean of weighted axes preserves 'weak link' behavior:
    a near-zero tractability collapses the score.
    """
    parts = [
        axes.impact ** profile.weight_impact,
        axes.neglectedness ** profile.weight_neglectedness,
        axes.tractability ** profile.weight_tractability,
        axes.surprise ** profile.weight_surprise,
    ]
    geo = math.prod(parts) ** (1.0 / max(len(parts), 1))
    risk_factor = max(0.0, 1.0 - axes.risk)
    score = geo * axes.answerability * risk_factor / (axes.cost_proxy + eps)
    # Normalize roughly into [0, 1] for display (raw can exceed 1).
    return float(max(0.0, min(1.5, score)))


def passes_gates(
    axes: ScoreAxes,
    gap_status: GapStatus,
    profile: ValueProfile,
) -> tuple[bool, list[str]]:
    flags: list[str] = []
    ok = True

    if axes.answerability < profile.min_answerability:
        ok = False
        flags.append("low_answerability")
    if axes.risk > profile.max_risk:
        ok = False
        flags.append("risk_reject")
    if gap_status == GapStatus.LIKELY_ANSWERED:
        ok = False
        flags.append("likely_answered")
    return ok, flags


def confidence_from_signals(
    judge_scores: list[ScoreAxes] | None,
    gap_confidence: float,
    literature_hit_count: int,
    *,
    heuristic: bool = False,
    gap_status: GapStatus | None = None,
) -> float:
    """Lower confidence when judges disagree or literature is thin."""
    base = 0.35 + 0.25 * gap_confidence
    if literature_hit_count == 0:
        base -= 0.12
    elif literature_hit_count >= 5:
        base += 0.08

    if gap_status == GapStatus.UNANSWERED and literature_hit_count > 0:
        # Neighborhood inspected and no strong answer match → more trustworthy.
        base += 0.06
    if gap_status == GapStatus.UNKNOWN_WITH_CAVEAT:
        base -= 0.05

    if judge_scores and len(judge_scores) >= 2:
        impacts = [j.impact for j in judge_scores]
        spread = statistics.pstdev(impacts) if len(impacts) > 1 else 0.0
        base -= min(0.25, spread * 0.6)

    if heuristic:
        base = min(base, 0.58)

    return float(max(0.05, min(0.95, base)))


def heuristic_score(
    q: UnansweredQuestion,
    gap_status: GapStatus,
    related_count: int,
    avg_citations: float,
    profile: ValueProfile,
    strong_match_count: int = 0,
) -> ScoreAxes:
    """
    Offline / fallback scorer when LLM judges are unavailable.
    Uses linguistic + literature density cues — lower confidence expected.
    """
    text = f"{q.question} {q.why_it_matters} {q.operationalization}".lower()
    impact_keywords = (
        "mortal", "death", "climate", "pandemic", "energy", "alignment",
        "extinction", "cancer", "antibiotic", "fusion", "consciousness",
        "aging", "famine", "biosecurity", "civilization",
    )
    surprise_keywords = (
        "unknown", "paradox", "unexplained", "contradict", "mechanism",
        "why does", "missing link", "first principles",
    )
    hard_keywords = (
        "prove", "forever", "meaning of life", "free will", "should we",
    )

    impact = 0.35 + 0.08 * sum(1 for k in impact_keywords if k in text)
    surprise = 0.3 + 0.07 * sum(1 for k in surprise_keywords if k in text)
    answerability = 0.7
    if any(k in text for k in hard_keywords):
        answerability -= 0.25
    if "?" not in q.question and not q.question.lower().startswith(
        ("what", "why", "how", "which", "when", "where", "can", "does", "is")
    ):
        answerability -= 0.15
    if len(q.operationalization) < 40:
        answerability -= 0.1
    if len(q.operationalization) >= 80:
        answerability = min(1.0, answerability + 0.08)

    # Neglectedness: penalize strong answer-like matches more than weak neighborhood.
    density = min(1.0, related_count / 25.0)
    answer_pressure = min(1.0, strong_match_count / 4.0)
    cite_pressure = min(1.0, avg_citations / 200.0)
    neglectedness = max(
        0.05,
        1.0 - 0.35 * density - 0.45 * answer_pressure - 0.2 * cite_pressure,
    )

    if gap_status == GapStatus.UNANSWERED:
        neglectedness = min(1.0, neglectedness + 0.12)
        surprise = min(1.0, surprise + 0.05)
        answerability = min(1.0, answerability + 0.05)
    elif gap_status == GapStatus.PARTIALLY_ANSWERED:
        neglectedness *= 0.85
    elif gap_status == GapStatus.LIKELY_ANSWERED:
        neglectedness *= 0.4
        answerability *= 0.7

    tractability = 0.55
    if "measure" in text or "experiment" in text or "dataset" in text:
        tractability += 0.15
    if "quantum gravity" in text or "consciousness" in text:
        tractability -= 0.2
    if profile.prefer_interdisciplinary and len(q.tags) >= 2:
        impact = min(1.0, impact + 0.05)

    risk = 0.15
    if any(k in text for k in ("weapon", "pathogen", "bioweapon", "surveillance")):
        risk = 0.9

    cost = 0.45
    if "large-scale" in text or "longitudinal" in text or "clinical trial" in text:
        cost = 0.7

    def clamp(x: float) -> float:
        return float(max(0.0, min(1.0, x)))

    return ScoreAxes(
        impact=clamp(impact),
        neglectedness=clamp(neglectedness),
        tractability=clamp(tractability),
        surprise=clamp(surprise),
        answerability=clamp(answerability),
        risk=clamp(risk),
        cost_proxy=clamp(cost),
        rationale={
            "method": "heuristic_density_and_lexicon",
            "note": "Fallback scorer; prefer LLM judges when available.",
            "strong_match_count": str(strong_match_count),
        },
    )
