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
from artificial_curiosity.safety import DualUseAssessment, assess_dual_use


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
        axes.impact**profile.weight_impact,
        axes.neglectedness**profile.weight_neglectedness,
        axes.tractability**profile.weight_tractability,
        axes.surprise**profile.weight_surprise,
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
    disagreement_entropy: float = 0.0,
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

    if disagreement_entropy > 0:
        base -= min(0.2, disagreement_entropy * 0.35)

    if heuristic:
        base = min(base, 0.58)

    return float(max(0.05, min(0.95, base)))


def score_uncertainty_band(
    curiosity_score: float,
    confidence: float,
    *,
    heuristic: bool = False,
    disagreement_entropy: float = 0.0,
) -> tuple[float, float]:
    """
    Evidence-strength envelope around the point score (F8 mitigation).

    Not a statistical CI — width grows as confidence falls / heuristic mode /
    multi-judge disagreement (W15).
    """
    half = 0.08 + 0.22 * (1.0 - confidence)
    if heuristic:
        half += 0.04
    if disagreement_entropy > 0:
        half += 0.12 * min(1.0, disagreement_entropy)
    low = max(0.0, curiosity_score - half)
    high = min(1.5, curiosity_score + half)
    return float(low), float(high)


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

    Encodes FIRST_PRINCIPLES + FAILURE_MODES:
    - F3: citations affect neglectedness only — never inflate impact (anti-McNamara)
    - F6: literature density / strong matches reduce neglectedness (anti-trend-chase)
    - F9: multi-clause research programs lose answerability (anti-scope-creep)
    - F10: dual-use keywords raise risk
    - F14: expensive investigations raise cost_proxy (cuts aggregate score)
    """
    text = f"{q.question} {q.why_it_matters} {q.operationalization}".lower()
    q_only = q.question.lower()
    impact_keywords = (
        "mortal",
        "death",
        "climate",
        "pandemic",
        "energy",
        "alignment",
        "extinction",
        "cancer",
        "antibiotic",
        "fusion",
        "consciousness",
        "aging",
        "famine",
        "biosecurity",
        "civilization",
    )
    surprise_keywords = (
        "unknown",
        "paradox",
        "unexplained",
        "contradict",
        "mechanism",
        "why does",
        "missing link",
        "first principles",
    )
    hard_keywords = (
        "prove",
        "forever",
        "meaning of life",
        "free will",
        "should we",
    )

    # Impact from stake language only — never from citation counts (F3).
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

    # F9: one primary unknown — punish research-program sprawl.
    if q.question.count("?") > 1:
        answerability -= 0.2
    if q_only.count(" and ") >= 2 and len(q.operationalization) < 100:
        answerability -= 0.12
    if len(q.enabling_questions) > 4:
        answerability -= 0.08

    # Neglectedness: density + answer pressure + cites — NOT impact (F3/F6).
    # WO-0.4.4: thin funding / trend / interdisciplinary proxies (still heuristic).
    density = min(1.0, related_count / 25.0)
    answer_pressure = min(1.0, strong_match_count / 4.0)
    cite_pressure = min(1.0, avg_citations / 200.0)
    neglectedness = max(
        0.05,
        1.0 - 0.35 * density - 0.45 * answer_pressure - 0.2 * cite_pressure,
    )

    hot_topic = (
        "transformer",
        "llm",
        "chatgpt",
        "foundation model",
        "hype",
        "blockchain",
        "nft",
        "metaverse",
    )
    funding_heavy = (
        "well-funded",
        "heavily funded",
        "billion-dollar",
        "arms race",
        "industry standard",
        "saturated field",
        "crowded literature",
    )
    neglected_cues = (
        "understudied",
        "neglected",
        "orphan",
        "under-funded",
        "underfunded",
        "few papers",
        "little attention",
        "overlooked",
        "sparse literature",
    )
    if any(k in text for k in hot_topic):
        neglectedness *= 0.82  # F6: resist trend chasing
    if any(k in text for k in funding_heavy):
        neglectedness *= 0.78
    if any(k in text for k in neglected_cues):
        neglectedness = min(1.0, neglectedness + 0.1)
    # Interdisciplinary tags often mark thinner literature seams (proxy only).
    if len(q.tags) >= 3:
        neglectedness = min(1.0, neglectedness + 0.06)

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

    # F10: weighted dual-use classifier (beyond lone keywords) — see safety.py.
    dual: DualUseAssessment = assess_dual_use(text)
    risk = max(0.15, dual.risk)

    # Cost proxy (F14 / WO-0.4.4): scale of investigation language.
    cost = 0.45
    if any(
        k in text
        for k in (
            "pilot",
            "small-n",
            "simulation",
            "reanalysis",
            "meta-analysis",
            "existing dataset",
            "retrospective",
        )
    ):
        cost = min(cost, 0.32)
    if "large-scale" in text or "longitudinal" in text or "clinical trial" in text:
        cost = 0.7
    if any(
        k in text
        for k in (
            "multi-decade",
            "nationwide",
            "particle collider",
            "space mission",
            "phase iii",
            "phase 3",
            "rct with n>",
            "animal colony",
        )
    ):
        cost = max(cost, 0.85)
    if "multi-site" in text or "multi-center" in text or "international cohort" in text:
        cost = max(cost, 0.75)

    def clamp(x: float) -> float:
        return float(max(0.0, min(1.0, x)))

    rationale = {
        "method": "heuristic_density_and_lexicon",
        "note": (
            "Fallback scorer; prefer LLM judges when available. "
            "Citations affect neglectedness only (anti-McNamara). "
            "Neglectedness/cost use thin proxies (density, funding/trend cues, "
            "investigation-scale language) — not funding databases. "
            "Dual-use via weighted_heuristic_v1 (not a biosafety oracle). "
            "openalex_hit_n / mean_cited_by / funder_field_missing_rate are "
            "rationale keys only — they do not silently rewrite weights."
        ),
        "strong_match_count": str(strong_match_count),
        "value_profile": profile.name,
        "dual_use_method": dual.method,
        "neglectedness_proxy": "density_cites_trend_funding_cues_v1",
        "cost_proxy_method": "investigation_scale_lexicon_v1",
        # Funding/OpenAlex transparency keys (research/FUNDING_NEGLECT_SIGNALS.md).
        "openalex_hit_n": str(int(related_count)),
        "mean_cited_by": f"{float(avg_citations):.1f}",
    }
    if dual.signals:
        rationale["dual_use_signals"] = ",".join(dual.signals[:6])
    if dual.needs_human_review:
        rationale["human_review"] = "near_threshold_or_high_risk"

    return ScoreAxes(
        impact=clamp(impact),
        neglectedness=clamp(neglectedness),
        tractability=clamp(tractability),
        surprise=clamp(surprise),
        answerability=clamp(answerability),
        risk=clamp(risk),
        cost_proxy=clamp(cost),
        rationale=rationale,
    )


def lit_rationale_keys(related_works: list | None) -> dict[str, str]:
    """
    Optional OpenAlex-ish transparency keys for neglectedness *display*.

    Never feed these into weight changes by themselves — attach to rationale only.
    """
    works = list(related_works or [])
    n = len(works)
    cites = [getattr(h, "cited_by_count", None) for h in works]
    cite_vals = [float(c) for c in cites if c is not None]
    mean_cites = sum(cite_vals) / len(cite_vals) if cite_vals else 0.0
    funder_flags = [getattr(h, "has_funder", None) for h in works]
    known = [f for f in funder_flags if f is not None]
    if not known:
        missing_rate = "1.0"
        note = "funder_metadata_unavailable"
    else:
        missing = sum(1 for f in known if not f) / len(known)
        missing_rate = f"{missing:.3f}"
        note = "from_has_funder_field"
    return {
        "openalex_hit_n": str(n),
        "mean_cited_by": f"{mean_cites:.1f}",
        "funder_field_missing_rate": missing_rate,
        "funder_metadata_note": note,
    }


def dual_use_flags(text: str, profile: ValueProfile) -> list[str]:
    """Flags for pipeline: human_review_risk / dual_use_high (WO-0.4.2)."""
    dual = assess_dual_use(text)
    flags: list[str] = []
    if dual.needs_human_review:
        flags.append("human_review_risk")
    if dual.hard_reject_likely or dual.risk > profile.max_risk:
        flags.append("dual_use_high")
    return flags
