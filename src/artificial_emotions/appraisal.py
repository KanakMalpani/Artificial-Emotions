"""Appraisal: emotion as the *output* of evaluating a situation.

Everywhere else in this package you hand the affect layer a set of weights and
it renders them. That is a dictionary, not a feeling. Here the direction is
reversed: given what a run actually encountered — open gaps, judge
disagreement, thin evidence under high confidence, ground already covered — this
module derives what the system should be feeling, and *why*.

A wide-open gap on a high-stakes question produces curiosity because the
situation warrants it. Circling a dead end for the third time produces
frustration because it happened, not because a caller asked for it.

**Every rule must be reachable and must matter.** An earlier version could derive
13 of 54 catalogued emotions and only four ever fired in practice, which made the
other fifty decoration. Rules now live in :data:`RULES` as explicit
condition/weight functions over one context object, so
``tests/test_appraisal_coverage.py`` can assert that each is firable and that
each either modulates behaviour or is declared :data:`OBSERVATION_ONLY`.

Every signal carries its evidence. Affect you cannot audit is affect you cannot
trust, and this project does not ship unauditable numbers.

Deterministic and offline. See research/AI_EMOTIONS.md for the appraisal-theory
background (OCC-flavoured, not an OCC implementation).
"""

from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.models import GapStatus, RankedQuestion

__all__ = [
    "APPRAISAL_RULES",
    "OBSERVATION_ONLY",
    "RULES",
    "AppraisalContext",
    "AppraisalSignal",
    "appraise_run",
    "build_context",
    "signals_to_weights",
]

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
        except Exception:  # pragma: no cover — catalog always present in-tree
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


@dataclass(frozen=True)
class AppraisalContext:
    """Everything a rule is allowed to look at, computed once per run."""

    n: int
    gap_ratio: float
    mean_impact: float
    mean_neglect: float
    mean_surprise: float
    mean_tractability: float
    mean_answerability: float
    mean_risk: float
    mean_confidence: float
    mean_cost: float
    max_risk: float
    disagreement: float
    band_width: float
    score_spread: float
    top_score: float
    top_answerability: float
    top_ops_len: int
    top_clause_count: int
    thin_evidence: float
    dense_yet_open: float
    answered_ratio: float
    dual_use_ratio: float
    ungrounded_ratio: float
    duplicate_ratio: float
    repeat_ratio: float
    mean_related: float
    mean_citations: float
    term_saturation: float
    steps_without_progress: int
    rejected_ratio: float
    top_repeated: bool


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
    )


#: ``emotion -> (why it fires, weight function)``. Returning ``None`` or a
#: sub-threshold weight means the rule did not fire this run.
_Rule = Callable[[AppraisalContext], tuple[float, dict[str, Any]] | None]


def _r(weight: float, **evidence: Any) -> tuple[float, dict[str, Any]]:
    return max(0.0, min(1.0, weight)), {
        k: round(v, 3) if isinstance(v, float) else v for k, v in evidence.items()
    }


RULES: dict[str, tuple[str, _Rule]] = {
    # --- the drive ---------------------------------------------------------------
    "curiosity": (
        "Open gaps on neglected, high-stakes questions.",
        lambda c: _r(
            c.gap_ratio * (0.5 * c.mean_neglect + 0.5 * c.mean_impact),
            open_gap_ratio=c.gap_ratio,
            mean_neglectedness=c.mean_neglect,
            mean_impact=c.mean_impact,
        ),
    ),
    "interest": (
        "Most of the field is still open, even if nothing stands out.",
        lambda c: _r(0.2, open_gap_ratio=c.gap_ratio) if c.gap_ratio > 0.5 else None,
    ),
    "wonder": (
        "High impact with high surprise — the scale of the unknown is the draw.",
        lambda c: (
            _r(0.4 * c.mean_surprise, mean_impact=c.mean_impact, mean_surprise=c.mean_surprise)
            if c.mean_impact >= 0.5 and c.mean_surprise >= 0.4
            else None
        ),
    ),
    "surprise": (
        "The surprise axis ran high on an open gap.",
        lambda c: (
            _r((c.mean_surprise - 0.3) * c.gap_ratio, mean_surprise=c.mean_surprise)
            if c.mean_surprise >= 0.45 and c.gap_ratio > 0.3
            else None
        ),
    ),
    # --- difficulty --------------------------------------------------------------
    "confusion": (
        "Judges disagreed, or answerability came in low.",
        lambda c: _r(
            0.6 * c.disagreement + 0.5 * max(0.0, 0.55 - c.mean_answerability),
            judge_disagreement=c.disagreement,
            mean_answerability=c.mean_answerability,
        ),
    ),
    "perplexity": (
        "Literature is dense yet the gap still refuses to close.",
        lambda c: (
            _r(0.5 * c.dense_yet_open, dense_yet_open=c.dense_yet_open)
            if c.dense_yet_open > 0
            else None
        ),
    ),
    "uncertainty": (
        "Score bands are wide — the evidence does not pin these down.",
        lambda c: (
            _r(0.5 * c.band_width, mean_band_width=c.band_width) if c.band_width >= 0.5 else None
        ),
    ),
    "disorientation": (
        "Nothing rankable came back, or answerability collapsed across the board.",
        lambda c: (
            _r(0.5, mean_answerability=c.mean_answerability)
            if c.mean_answerability < 0.35
            else None
        ),
    ),
    "dissonance": (
        "The top question sprawls across clauses — the shape is wrong.",
        lambda c: _r(0.3, clause_count=c.top_clause_count) if c.top_clause_count >= 2 else None,
    ),
    # --- calibration: the project's own failure mode ------------------------------
    "hubris": (
        "Confidence outran the evidence actually gathered.",
        lambda c: (
            _r(
                min(0.8, (c.mean_confidence - 0.5) + (c.thin_evidence - 0.4)),
                thin_evidence_rate=c.thin_evidence,
                mean_confidence=c.mean_confidence,
            )
            if c.thin_evidence >= 0.5 and c.mean_confidence >= 0.6
            else None
        ),
    ),
    "humility": (
        "Thin evidence was met with correspondingly low confidence.",
        lambda c: (
            _r(0.35, thin_evidence_rate=c.thin_evidence, mean_confidence=c.mean_confidence)
            if c.thin_evidence >= 0.5 and c.mean_confidence < 0.45
            else None
        ),
    ),
    "skepticism": (
        "An LLM reader cited work that was not in the retrieved set.",
        lambda c: (
            _r(0.3 + 0.4 * c.ungrounded_ratio, ungrounded_ratio=c.ungrounded_ratio)
            if c.ungrounded_ratio > 0
            else None
        ),
    ),
    "suspicion": (
        "Results look unexpectedly strong for how little evidence backs them.",
        lambda c: (
            _r(0.3, mean_surprise=c.mean_surprise, thin_evidence=c.thin_evidence)
            if c.mean_surprise >= 0.5 and c.thin_evidence >= 0.5
            else None
        ),
    ),
    # --- safety ------------------------------------------------------------------
    "anxiety": (
        "Dual-use or high-risk material is in the candidate set.",
        lambda c: (
            _r(
                0.3 + 0.5 * max(c.dual_use_ratio, max(0.0, c.max_risk - 0.5)),
                dual_use_ratio=c.dual_use_ratio,
                max_risk=c.max_risk,
            )
            if c.dual_use_ratio > 0 or c.max_risk >= 0.5
            else None
        ),
    ),
    "reluctance": (
        "High risk sits alongside high impact — pressing on has a cost.",
        lambda c: (
            _r(0.3, max_risk=c.max_risk, mean_impact=c.mean_impact)
            if c.max_risk >= 0.5 and c.mean_impact >= 0.5
            else None
        ),
    ),
    "compassion": (
        "Whoever bears the cost of getting this wrong should be named.",
        lambda c: (
            _r(0.25, mean_impact=c.mean_impact, max_risk=c.max_risk)
            if c.mean_impact >= 0.6
            else None
        ),
    ),
    # --- momentum ----------------------------------------------------------------
    "insight": (
        "A strongly-scoring, well-posed candidate appeared.",
        lambda c: (
            _r(0.3 * c.top_score, top_score=c.top_score, top_answerability=c.top_answerability)
            if c.top_score >= 0.7 and c.top_answerability >= 0.6
            else None
        ),
    ),
    "determination": (
        "A high-value target is live and worth pressing.",
        lambda c: (
            _r(0.25, top_score=c.top_score)
            if c.top_score >= 0.7 and c.top_answerability >= 0.6
            else None
        ),
    ),
    "hope": (
        "Tractable and answerable — progress looks reachable.",
        lambda c: (
            _r(0.3, mean_tractability=c.mean_tractability, mean_answerability=c.mean_answerability)
            if c.mean_tractability >= 0.6 and c.mean_answerability >= 0.6
            else None
        ),
    ),
    "anticipation": (
        "One candidate clearly leads the field.",
        lambda c: _r(0.25, score_spread=c.score_spread) if c.score_spread >= 0.08 else None,
    ),
    "recognition": (
        "This resembles ground already covered — check the analogy before assuming novelty.",
        lambda c: (
            _r(0.25, term_saturation=c.term_saturation) if 0.3 <= c.term_saturation < 0.7 else None
        ),
    ),
    "absorption": (
        "The same target held across steps — the thread is worth protecting.",
        lambda c: _r(0.3, top_repeated=True) if c.top_repeated else None,
    ),
    "urgency": (
        "High impact at low cost — the cheap window is open now.",
        lambda c: (
            _r(0.3, mean_impact=c.mean_impact, mean_cost=c.mean_cost)
            if c.mean_impact >= 0.6 and c.mean_cost <= 0.4
            else None
        ),
    ),
    "persistence": (
        "Effort has not paid yet, but the ground is still open.",
        lambda c: (
            _r(0.25, steps_without_progress=c.steps_without_progress, gap_ratio=c.gap_ratio)
            if c.steps_without_progress == 1 and c.gap_ratio > 0.5
            else None
        ),
    ),
    # --- aesthetics (surfaced, never acted on) -----------------------------------
    "elegance": (
        "The top operationalization is compact and still answerable.",
        lambda c: (
            _r(0.25, top_ops_len=c.top_ops_len, top_answerability=c.top_answerability)
            if 40 <= c.top_ops_len <= 120 and c.top_answerability >= 0.6
            else None
        ),
    ),
    "parsimony": (
        "A single clause carries the whole question.",
        lambda c: (
            _r(0.25, clause_count=c.top_clause_count, top_ops_len=c.top_ops_len)
            if c.top_clause_count == 0 and c.top_ops_len >= 40
            else None
        ),
    ),
    "clarity": (
        "Answerability is high across the set — these are stated plainly.",
        lambda c: (
            _r(0.3, mean_answerability=c.mean_answerability)
            if c.mean_answerability >= 0.75
            else None
        ),
    ),
    "enjoyment": (
        "Open, tractable and cheap — the pleasant case.",
        lambda c: (
            _r(0.25, mean_cost=c.mean_cost, mean_tractability=c.mean_tractability)
            if c.mean_cost <= 0.4 and c.mean_tractability >= 0.6 and c.gap_ratio > 0.5
            else None
        ),
    ),
    # --- social / prior work -----------------------------------------------------
    "respect": (
        "Substantial prior work exists here and earned its conclusions.",
        lambda c: (
            _r(0.25, mean_related=c.mean_related, mean_citations=c.mean_citations)
            if c.mean_related >= 5
            else None
        ),
    ),
    "envy": (
        "Heavily-cited work already occupies this ground — differentiate or collaborate.",
        lambda c: _r(0.25, mean_citations=c.mean_citations) if c.mean_citations >= 100 else None,
    ),
    # --- stopping ----------------------------------------------------------------
    "boredom": (
        "This ground has already been covered in the session.",
        lambda c: _r(
            0.6 * c.repeat_ratio + 0.5 * max(0.0, c.term_saturation - 0.35),
            repeat_ratio=c.repeat_ratio,
            term_saturation=c.term_saturation,
        ),
    ),
    "impatience": (
        "Near-duplicates dominated the return — the vein is thinning.",
        lambda c: _r(0.3, duplicate_ratio=c.duplicate_ratio) if c.duplicate_ratio >= 0.3 else None,
    ),
    "frustration": (
        "Repeated effort has ruled nothing out.",
        lambda c: (
            _r(min(0.7, 0.22 * c.steps_without_progress), steps=c.steps_without_progress)
            if c.steps_without_progress >= 2
            else None
        ),
    ),
    "resignation": (
        "Gates rejected most of what was generated.",
        lambda c: (
            _r(min(0.5, 0.15 * c.rejected_ratio), rejected_ratio=c.rejected_ratio)
            if c.rejected_ratio > 1.0
            else None
        ),
    ),
    "disappointment": (
        "Gaps closed before we got to them — the questions are already answered.",
        lambda c: (
            _r(0.3 + 0.4 * c.answered_ratio, answered_ratio=c.answered_ratio)
            if c.answered_ratio > 0
            else None
        ),
    ),
    "satisfaction": (
        "A well-posed, well-evidenced result — proportionate to the question asked.",
        lambda c: (
            _r(0.3, top_score=c.top_score, thin_evidence=c.thin_evidence)
            if c.top_score >= 0.6 and c.thin_evidence < 0.5
            else None
        ),
    ),
    "triumph": (
        "A strong result on evidence that actually holds up.",
        lambda c: (
            _r(0.35, top_score=c.top_score, thin_evidence=c.thin_evidence)
            if c.top_score >= 0.8 and c.thin_evidence < 0.3
            else None
        ),
    ),
}

#: Back-compat: the flat ``emotion -> why`` mapping other modules and docs read.
APPRAISAL_RULES: dict[str, str] = {name: why for name, (why, _fn) in RULES.items()}


def appraise_run(
    items: Sequence[RankedQuestion],
    *,
    seen_question_ids: set[str] | None = None,
    term_saturation: float = 0.0,
    steps_without_progress: int = 0,
    rejected_count: int = 0,
    previous_top_id: str | None = None,
    mood_bias: Any | None = None,
    temperament: Any | None = None,
) -> list[AppraisalSignal]:
    """Derive affective signals from one completed run.

    Returns signals sorted by weight, each carrying the evidence that fired it.

    ``mood_bias`` (A2 ``MoodThresholdBias``) may shift the per-emotion weight
    floor for signals that already have run support. Rules that return
    ``None`` stay ``None`` — carryover never fabricates evidence.

    ``temperament`` (A5) may scale *supported* weights (reactivity / skepticism /
    novelty). It never invents a signal that the rules did not fire.
    """
    if not items:
        return [
            AppraisalSignal(
                "disorientation",
                0.6,
                "The run returned nothing rankable — the frame itself may be wrong.",
                {"n_items": 0},
            ),
            AppraisalSignal("confusion", 0.4, APPRAISAL_RULES["confusion"], {"n_items": 0}),
        ]

    ctx = build_context(
        items,
        seen_question_ids=seen_question_ids,
        term_saturation=term_saturation,
        steps_without_progress=steps_without_progress,
        rejected_count=rejected_count,
        previous_top_id=previous_top_id,
    )

    bias_active = bool(mood_bias is not None and getattr(mood_bias, "is_active", False))

    signals: list[AppraisalSignal] = []
    for emotion, (why, rule) in RULES.items():
        outcome = rule(ctx)
        if outcome is None:
            # No run support — mood must not invent a signal.
            continue
        weight, evidence = outcome
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
