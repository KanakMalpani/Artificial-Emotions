"""Appraisal: emotion as the *output* of evaluating a situation.

Everywhere else in this package you hand the affect layer a set of weights and
it renders them. That is a dictionary, not a feeling. Here the direction is
reversed: given what a run actually encountered — open gaps, judge
disagreement, thin evidence under high confidence, ground already covered — this
module derives what the system should be feeling, and *why*.

A wide-open gap on a high-stakes question produces curiosity because the
situation warrants it. Circling a dead end for the third time produces
frustration because it happened, not because a caller asked for it.

**Every catalog emotion must have a condition and a use.** An earlier version
could derive 13 of 54 catalogued emotions and only four ever fired in practice,
which made the other fifty decoration. The catalog is the **runtime** contract:
production dispatch evaluates catalog ``when`` only — empty ``when`` does not
fire. Coverage still asserts a non-empty ``when`` (or an ``outcome_event``
fixture) and a real use, and that each catalogued emotion is firable and either
modulates behaviour or is declared :data:`OBSERVATION_ONLY`.

Every signal carries its evidence. Affect you cannot audit is affect you cannot
trust, and this project does not ship unauditable numbers.

Deterministic and offline. See research/AI_EMOTIONS.md for the appraisal-theory
background (OCC-flavoured, not an OCC implementation).

Catalog ``when`` evaluation lives in ``appraisal_interpreter``; this module
keeps the public import path and run dispatch (``appraise_run``).
"""

from __future__ import annotations

import statistics
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.appraisal_interpreter import (
    CATALOG_SCHEMA_KEYS,
    CATALOG_WHEN_FEATURES,
    COERCION_LEVELS,
    EFFECT_IDS,
    REQUIRES_TOKENS,
    WEIGHT_EXPR_OPS,
    WHEN_OPS,
    AppraisalContext,
    context_feature,
    evaluate_when,
    validate_catalog_entry,
    validate_emotion_catalog,
    when_evidence,
)
from artificial_emotions.logutil import get_logger, soft_fail
from artificial_emotions.models import GapStatus, RankedQuestion

__all__ = [
    "APPRAISAL_USE_FOR",
    "CATALOG_SCHEMA_KEYS",
    "CATALOG_WHEN_FEATURES",
    "COERCION_LEVELS",
    "EFFECT_IDS",
    "OBSERVATION_ONLY",
    "REQUIRES_TOKENS",
    "WEIGHT_EXPR_OPS",
    "WHEN_OPS",
    "AppraisalContext",
    "AppraisalSignal",
    "appraise_run",
    "build_context",
    "context_feature",
    "evaluate_when",
    "signals_to_weights",
    "validate_catalog_entry",
    "validate_emotion_catalog",
]

logger = get_logger("appraisal")

# Lazy catalog PAD lookup for mood-congruent threshold floors (A2).
_EMOTION_PAD_P: dict[str, float] | None = None


def _emotion_pad_p(emotion: str) -> float | None:
    global _EMOTION_PAD_P
    if _EMOTION_PAD_P is None:
        try:
            from artificial_emotions.emotions import emotion_catalog

            _EMOTION_PAD_P = {
                str(e["id"]): float((e.get("pad") or {}).get("P") or 0.0)
                for e in emotion_catalog().get("emotions") or []
            }
        except Exception as exc:  # pragma: no cover — catalog always present in-tree
            soft_fail(logger, "emotion catalog PAD lookup failed; mood floors disabled", exc=exc)
            _EMOTION_PAD_P = {}
    return _EMOTION_PAD_P.get(emotion)


# Below this a signal is noise; it gets dropped rather than padding the mix.
_MIN_SIGNAL = 0.04

#: Emotions that are appraised but deliberately change nothing. Aesthetic pull
#: and social comparison are real drivers of research choices *and* known biases,
#: so the system surfaces them for the reader instead of acting on them.
OBSERVATION_ONLY: frozenset[str] = frozenset(
    {
        "elegance",
        "parsimony",
        "dissonance",
        "envy",
        "respect",
        "compassion",
        "recognition",
        "clarity",
        "wonder",
        "enjoyment",
        "uncertainty",
        "interest",
        "surprise",
        "insight",
        "humility",
        "doubt",
        "conviction",
        "trust",
        "awe",
        "sublimity",
    }
)


@dataclass(frozen=True)
class AppraisalSignal:
    """One emotion, the weight it fired at, and the evidence behind it."""

    emotion: str
    weight: float
    because: str
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "emotion": self.emotion,
            "weight": round(float(self.weight), 4),
            "because": self.because,
            "evidence": self.evidence,
        }


def _catalog_by_id() -> dict[str, Mapping[str, Any]]:
    from artificial_emotions.emotions import emotion_catalog

    out: dict[str, Mapping[str, Any]] = {}
    for entry in emotion_catalog().get("emotions") or []:
        if isinstance(entry, Mapping) and entry.get("id"):
            out[str(entry["id"])] = entry
    return out


def _mean(values: Sequence[float]) -> float:
    vals = [float(v) for v in values]
    return sum(vals) / len(vals) if vals else 0.0


def _rate(items: Sequence[RankedQuestion], flag: str) -> float:
    if not items:
        return 0.0
    return sum(1 for i in items if flag in (i.flags or [])) / len(items)


def build_context(
    items: Sequence[RankedQuestion],
    *,
    seen_question_ids: set[str] | None = None,
    term_saturation: float = 0.0,
    steps_without_progress: int = 0,
    rejected_count: int = 0,
    previous_top_id: str | None = None,
    previous_max_risk: float = 0.0,
    previous_hubris: float = 0.0,
    outcome_result: str = "",
    outcome_question_id: str = "",
) -> AppraisalContext:
    """Reduce a run to the numbers the rules reason over."""
    seen = seen_question_ids or set()
    n = len(items)
    top = items[0]
    open_gaps = [
        i for i in items if i.gap.status in (GapStatus.UNANSWERED, GapStatus.UNKNOWN_WITH_CAVEAT)
    ]
    scores = [i.curiosity_score for i in items]
    bands = [
        (i.score_high - i.score_low)
        for i in items
        if i.score_high is not None and i.score_low is not None
    ]
    ops = top.question.operationalization or ""
    return AppraisalContext(
        n=n,
        gap_ratio=len(open_gaps) / n,
        mean_impact=_mean([i.scores.impact for i in items]),
        mean_neglect=_mean([i.scores.neglectedness for i in items]),
        mean_surprise=_mean([i.scores.surprise for i in items]),
        mean_tractability=_mean([i.scores.tractability for i in items]),
        mean_answerability=_mean([i.scores.answerability for i in items]),
        mean_risk=_mean([i.scores.risk for i in items]),
        mean_confidence=_mean([i.confidence for i in items]),
        mean_cost=_mean([i.scores.cost_proxy for i in items]),
        max_risk=max((i.scores.risk for i in items), default=0.0),
        disagreement=_mean(
            [float(i.metadata.get("judge_disagreement_entropy") or 0.0) for i in items]
        ),
        band_width=_mean(bands),
        score_spread=statistics.pstdev(scores) if len(scores) > 1 else 0.0,
        top_score=top.curiosity_score,
        top_answerability=top.scores.answerability,
        top_ops_len=len(ops),
        top_clause_count=top.question.question.count("?") + ops.count(";"),
        thin_evidence=0.5 * _rate(items, "heuristic_scoring") + 0.5 * _rate(items, "no_literature"),
        dense_yet_open=(
            len([i for i in open_gaps if len(i.gap.related_works) >= 4]) / n if n else 0.0
        ),
        answered_ratio=(
            sum(1 for i in items if i.gap.status == GapStatus.LIKELY_ANSWERED) / n if n else 0.0
        ),
        dual_use_ratio=max(
            _rate(items, "dual_use_high"),
            _rate(items, "human_review_risk"),
            _rate(items, "risk_reject"),
        ),
        ungrounded_ratio=_rate(items, "llm_gap_ungrounded"),
        duplicate_ratio=_rate(items, "near_duplicate_suppressed"),
        repeat_ratio=(sum(1 for i in items if i.question.id in seen) / n if n else 0.0),
        mean_related=_mean([float(len(i.gap.related_works)) for i in items]),
        mean_citations=_mean(
            [
                _mean([float(h.cited_by_count or 0) for h in i.gap.related_works])
                for i in items
                if i.gap.related_works
            ]
        ),
        term_saturation=float(term_saturation),
        steps_without_progress=int(steps_without_progress),
        rejected_ratio=(rejected_count / n if n else 0.0),
        top_repeated=bool(previous_top_id and previous_top_id == top.question.id),
        previous_max_risk=float(previous_max_risk or 0.0),
        previous_hubris=float(previous_hubris or 0.0),
        previous_top_id=str(previous_top_id or ""),
        outcome_result=str(outcome_result or "").strip().lower(),
        outcome_question_id=str(outcome_question_id or "").strip(),
    )


#: Catalog ``use_for`` by emotion id — text, not RULES lambdas.
#: Empty-items confusion still uses this map (special-case, not catalog ``when``).
APPRAISAL_USE_FOR: dict[str, str] = {
    eid: str(entry.get("use_for") or "").strip() for eid, entry in _catalog_by_id().items()
}


def _signal_because(eid: str, entry: Mapping[str, Any]) -> str:
    """Catalog ``use_for`` when present; else description; else id."""
    use_for = str(entry.get("use_for") or "").strip()
    if use_for:
        return use_for
    return str(entry.get("description") or eid)


def appraise_run(
    items: Sequence[RankedQuestion],
    *,
    seen_question_ids: set[str] | None = None,
    term_saturation: float = 0.0,
    steps_without_progress: int = 0,
    rejected_count: int = 0,
    previous_top_id: str | None = None,
    previous_max_risk: float = 0.0,
    previous_hubris: float = 0.0,
    outcome_result: str = "",
    outcome_question_id: str = "",
    mood_bias: Any | None = None,
    temperament: Any | None = None,
) -> list[AppraisalSignal]:
    """Derive affective signals from one completed run.

    Returns signals sorted by weight, each carrying the evidence that fired it.

    Catalog ``when`` is the runtime contract. Each catalog id with a non-empty
    ``when`` is evaluated via :func:`evaluate_when`; empty ``when`` skips the
    id. ``because`` is catalog ``use_for`` when present, else ``description``,
    else the emotion id.

    ``mood_bias`` (A2 ``MoodThresholdBias``) may shift the per-emotion weight
    floor for signals that already have run support. A ``when`` that does not
    match stays unmatched — carryover never fabricates evidence.

    ``temperament`` (A5) may scale *supported* weights (reactivity / skepticism /
    novelty). It never invents a signal that the catalog did not fire.
    """
    if not items:
        return [
            AppraisalSignal(
                "disorientation",
                0.6,
                "The run returned nothing rankable — the frame itself may be wrong.",
                {"n_items": 0},
            ),
            AppraisalSignal("confusion", 0.4, APPRAISAL_USE_FOR["confusion"], {"n_items": 0}),
        ]

    ctx = build_context(
        items,
        seen_question_ids=seen_question_ids,
        term_saturation=term_saturation,
        steps_without_progress=steps_without_progress,
        rejected_count=rejected_count,
        previous_top_id=previous_top_id,
        previous_max_risk=previous_max_risk,
        previous_hubris=previous_hubris,
        outcome_result=outcome_result,
        outcome_question_id=outcome_question_id,
    )

    catalog = _catalog_by_id()
    bias_active = bool(mood_bias is not None and getattr(mood_bias, "is_active", False))

    signals: list[AppraisalSignal] = []

    def _emit(emotion: str, why: str, weight: float, evidence: dict[str, Any]) -> None:
        floor = _MIN_SIGNAL
        if bias_active:
            floor = float(mood_bias.floor_for(_emotion_pad_p(emotion)))
        if weight >= floor:
            if bias_active and abs(floor - _MIN_SIGNAL) > 1e-9:
                evidence = {
                    **evidence,
                    "mood_threshold_floor": round(floor, 4),
                }
            signals.append(AppraisalSignal(emotion, weight, why, evidence))

    for eid, entry in catalog.items():
        when = list(entry.get("when") or [])
        if not when:
            continue
        weight = evaluate_when(ctx, when)
        if weight is None:
            continue
        _emit(eid, _signal_because(eid, entry), weight, when_evidence(ctx, when))

    signals.sort(key=lambda s: (-s.weight, s.emotion))
    if temperament is not None:
        from artificial_emotions.temperament import scale_appraisal_signals

        signals = scale_appraisal_signals(signals, temperament)
    return signals


def signals_to_weights(
    signals: Sequence[AppraisalSignal],
    *,
    max_components: int = 6,
) -> dict[str, float]:
    """Collapse signals into a weight map ready for ``mix_emotions``.

    Keeps the heaviest components so the resulting mix stays legible rather than
    smearing across a dozen near-zero emotions.
    """
    ordered = sorted(signals, key=lambda s: (-s.weight, s.emotion))[: max(1, max_components)]
    weights = {s.emotion: float(s.weight) for s in ordered if s.weight > 0}
    return weights or {"curiosity": 1.0}
