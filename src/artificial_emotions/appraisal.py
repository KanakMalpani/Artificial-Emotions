"""Appraisal: emotion as the *output* of evaluating a situation.

Everywhere else in this package you hand the affect layer a set of weights and
it renders them. That is a dictionary, not a feeling. Here the direction is
reversed: given what a run actually encountered — open gaps, judge
disagreement, thin evidence under high confidence, ground already covered — this
module derives what the system should be feeling, and *why*.

That inversion is the whole point. A wide-open gap on a high-stakes question
produces curiosity because the situation warrants it. Circling a dead end for
the third time produces frustration because it happened, not because a caller
asked for it.

Every signal carries its evidence. Affect you cannot audit is affect you cannot
trust, and this project does not ship unauditable numbers.

Deterministic and offline. See research/AI_EMOTIONS.md for the appraisal-theory
background (OCC-flavoured, not an OCC implementation).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.models import GapStatus, RankedQuestion

__all__ = [
    "APPRAISAL_RULES",
    "AppraisalSignal",
    "appraise_run",
    "signals_to_weights",
]

# Weight floor — below this a signal is noise and gets dropped rather than
# padding the mix with near-zero components.
_MIN_SIGNAL = 0.04

#: Human-readable description of every rule, for docs and the `why` surface.
APPRAISAL_RULES: dict[str, str] = {
    "curiosity": "Open gaps on neglected, high-stakes questions.",
    "interest": "A workable question survived the gates.",
    "surprise": "The surprise axis ran high on an open gap.",
    "confusion": "Judges disagreed, or answerability came in low.",
    "perplexity": "Literature is dense yet the gap still refuses to close.",
    "hubris": "Confidence outran the evidence actually gathered.",
    "humility": "Thin evidence was met with correspondingly low confidence.",
    "boredom": "This ground has already been covered in the session.",
    "frustration": "Repeated effort has ruled nothing out.",
    "resignation": "Gates rejected most of what was generated.",
    "insight": "A strongly-scoring, well-posed candidate appeared.",
    "determination": "A high-value target is live and worth pressing.",
}


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


def _mean(values: Sequence[float]) -> float:
    vals = [float(v) for v in values]
    return sum(vals) / len(vals) if vals else 0.0


def _flag_rate(items: Sequence[RankedQuestion], flag: str) -> float:
    if not items:
        return 0.0
    return sum(1 for i in items if flag in (i.flags or [])) / len(items)


def appraise_run(
    items: Sequence[RankedQuestion],
    *,
    seen_question_ids: set[str] | None = None,
    term_saturation: float = 0.0,
    steps_without_progress: int = 0,
    rejected_count: int = 0,
) -> list[AppraisalSignal]:
    """Derive affective signals from one completed run.

    Args:
        items: what the engine returned, already ranked.
        seen_question_ids: ids encountered earlier in this session.
        term_saturation: 0..1, how much of this run's vocabulary is already mined.
        steps_without_progress: consecutive steps that ruled nothing out.
        rejected_count: candidates the gates threw out this run.

    Returns:
        Signals sorted by weight, each carrying the evidence that fired it.
    """
    signals: list[AppraisalSignal] = []
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

    seen = seen_question_ids or set()
    n = len(items)
    open_gaps = [
        i for i in items if i.gap.status in (GapStatus.UNANSWERED, GapStatus.UNKNOWN_WITH_CAVEAT)
    ]
    mean_neglect = _mean([i.scores.neglectedness for i in items])
    mean_impact = _mean([i.scores.impact for i in items])
    mean_surprise = _mean([i.scores.surprise for i in items])
    mean_answerability = _mean([i.scores.answerability for i in items])
    mean_confidence = _mean([i.confidence for i in items])
    top = items[0]

    # --- curiosity: the core drive — open gaps that are neglected and matter ---
    gap_ratio = len(open_gaps) / n
    curiosity = gap_ratio * (0.5 * mean_neglect + 0.5 * mean_impact)
    if curiosity >= _MIN_SIGNAL:
        signals.append(
            AppraisalSignal(
                "curiosity",
                curiosity,
                APPRAISAL_RULES["curiosity"],
                {
                    "open_gap_ratio": round(gap_ratio, 3),
                    "mean_neglectedness": round(mean_neglect, 3),
                    "mean_impact": round(mean_impact, 3),
                },
            )
        )

    # --- surprise -------------------------------------------------------------
    if mean_surprise >= 0.45 and gap_ratio > 0.3:
        signals.append(
            AppraisalSignal(
                "surprise",
                (mean_surprise - 0.3) * gap_ratio,
                APPRAISAL_RULES["surprise"],
                {"mean_surprise": round(mean_surprise, 3)},
            )
        )

    # --- confusion: disagreement or a question posed too loosely to attack ----
    disagreement = _mean(
        [float(i.metadata.get("judge_disagreement_entropy") or 0.0) for i in items]
    )
    confusion = 0.6 * disagreement + 0.5 * max(0.0, 0.55 - mean_answerability)
    if confusion >= _MIN_SIGNAL:
        signals.append(
            AppraisalSignal(
                "confusion",
                confusion,
                APPRAISAL_RULES["confusion"],
                {
                    "judge_disagreement": round(disagreement, 3),
                    "mean_answerability": round(mean_answerability, 3),
                },
            )
        )

    # --- perplexity: plenty of neighbours, still no resolution -----------------
    dense_but_open = [i for i in open_gaps if len(i.gap.related_works) >= 4]
    if dense_but_open:
        signals.append(
            AppraisalSignal(
                "perplexity",
                0.5 * (len(dense_but_open) / n),
                APPRAISAL_RULES["perplexity"],
                {"dense_yet_open": len(dense_but_open)},
            )
        )

    # --- hubris / humility: does confidence match the evidence gathered? ------
    # This is the project's own failure mode, so the system appraises itself for
    # it rather than waiting to be told.
    thin = _flag_rate(items, "heuristic_scoring") * 0.5 + _flag_rate(items, "no_literature") * 0.5
    if thin >= 0.5 and mean_confidence >= 0.6:
        signals.append(
            AppraisalSignal(
                "hubris",
                min(0.8, (mean_confidence - 0.5) + (thin - 0.4)),
                APPRAISAL_RULES["hubris"],
                {
                    "thin_evidence_rate": round(thin, 3),
                    "mean_confidence": round(mean_confidence, 3),
                },
            )
        )
    elif thin >= 0.5 and mean_confidence < 0.45:
        signals.append(
            AppraisalSignal(
                "humility",
                0.35,
                APPRAISAL_RULES["humility"],
                {
                    "thin_evidence_rate": round(thin, 3),
                    "mean_confidence": round(mean_confidence, 3),
                },
            )
        )

    # --- boredom: ground already covered --------------------------------------
    repeats = sum(1 for i in items if i.question.id in seen)
    repeat_ratio = repeats / n
    boredom = 0.6 * repeat_ratio + 0.5 * max(0.0, float(term_saturation) - 0.35)
    if boredom >= _MIN_SIGNAL:
        signals.append(
            AppraisalSignal(
                "boredom",
                boredom,
                APPRAISAL_RULES["boredom"],
                {
                    "already_seen": repeats,
                    "of": n,
                    "term_saturation": round(float(term_saturation), 3),
                },
            )
        )

    # --- frustration / resignation: effort that ruled nothing out -------------
    if steps_without_progress >= 2:
        signals.append(
            AppraisalSignal(
                "frustration",
                min(0.7, 0.22 * steps_without_progress),
                APPRAISAL_RULES["frustration"],
                {"steps_without_progress": steps_without_progress},
            )
        )
    if rejected_count > n:
        signals.append(
            AppraisalSignal(
                "resignation",
                min(0.5, 0.15 * (rejected_count / max(n, 1))),
                APPRAISAL_RULES["resignation"],
                {"rejected": rejected_count, "returned": n},
            )
        )

    # --- insight / determination: something good actually turned up -----------
    if top.curiosity_score >= 0.7 and top.scores.answerability >= 0.6:
        signals.append(
            AppraisalSignal(
                "insight",
                0.3 * top.curiosity_score,
                APPRAISAL_RULES["insight"],
                {
                    "top_score": round(top.curiosity_score, 3),
                    "top_answerability": round(top.scores.answerability, 3),
                },
            )
        )
        signals.append(
            AppraisalSignal(
                "determination",
                0.25,
                APPRAISAL_RULES["determination"],
                {"top_question_id": top.question.id},
            )
        )
    elif gap_ratio > 0.5:
        signals.append(
            AppraisalSignal(
                "interest",
                0.2,
                APPRAISAL_RULES["interest"],
                {"open_gap_ratio": round(gap_ratio, 3)},
            )
        )

    kept = [s for s in signals if s.weight >= _MIN_SIGNAL]
    kept.sort(key=lambda s: (-s.weight, s.emotion))
    return kept


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
