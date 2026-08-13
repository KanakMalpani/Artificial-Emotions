"""Stances: emotions as ways of working, not passengers in curiosity's loop.

The catalog kept growing and every emotion still ended up a bystander, because
there was exactly one entry point and it was a curiosity loop. Widening
appraisal made more of them *fire*; it did not give any of them a reason to be
the point of anything.

A stance fixes that. Each one is a different question you can ask of the same
ranked set, driven by a different cluster of emotions, and returning a genuinely
different view:

    doubt    — skepticism, suspicion, hubris, doubt, pride, shame
    safety   — anxiety, reluctance, compassion, fear, disgust
    focus    — absorption, determination, conviction, joy
    close    — disappointment, resignation, sadness, anger
    taste    — elegance, parsimony, dissonance
    wonder   — wonder, surprise, insight, intrigue
    survey   — respect, envy, recognition, trust, admiration, gratitude

Curiosity answers "what is worth investigating". These answer the other
questions a working researcher actually has, and each is useless in the others'
situation — which is the point. An emotion that is never the right lens for
anything was never doing work.

Deterministic and offline. Stances re-view an existing run; they never re-rank
it, so the ValueProfile ordering you were given is the ordering you keep.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from artificial_emotions.models import GapStatus, RankedQuestion

__all__ = [
    "STANCES",
    "Stance",
    "apply_stance",
    "list_stances",
]


@dataclass(frozen=True)
class Stance:
    """One way of looking at a ranked set."""

    name: str
    asks: str
    use_when: str
    driving_emotions: tuple[str, ...]
    lens: Callable[[Sequence[RankedQuestion]], dict[str, Any]] = field(repr=False)

    def describe(self) -> dict[str, Any]:
        return {
            "stance": self.name,
            "asks": self.asks,
            "use_when": self.use_when,
            "driving_emotions": list(self.driving_emotions),
        }


def _flags(item: RankedQuestion) -> set[str]:
    return set(item.flags or [])


def _band(item: RankedQuestion) -> float:
    if item.score_high is None or item.score_low is None:
        return 0.0
    return float(item.score_high - item.score_low)


# --- doubt ----------------------------------------------------------------------------


def _lens_doubt(items: Sequence[RankedQuestion]) -> dict[str, Any]:
    """Rank by how likely each item is to be *wrong*, not how attractive it is."""
    reviewed = []
    for item in items:
        flags = _flags(item)
        reasons: list[str] = []
        if "heuristic_scoring" in flags:
            reasons.append("scored heuristically — no judge looked at it")
        if "no_literature" in flags:
            reasons.append("no literature was consulted, so the gap is unverified")
        if "llm_gap_ungrounded" in flags:
            reasons.append("an LLM reader cited work that was not retrieved")
        if item.confidence < 0.4:
            reasons.append(f"confidence is low ({item.confidence:.2f})")
        if _band(item) >= 0.5:
            reasons.append(f"score band is wide ({_band(item):.2f}) — weakly pinned")
        if item.scores.answerability < 0.5:
            reasons.append("answerability is low — it may not be settleable as posed")
        if item.gap.status == GapStatus.UNKNOWN_WITH_CAVEAT:
            reasons.append("gap status is hedged, not established")
        if not item.gap.related_works:
            reasons.append("no related work was found to argue against")

        reviewed.append(
            {
                "question_id": item.question.id,
                "question": item.question.question,
                "rank_by_curiosity": item.rank,
                "doubt_score": round(min(1.0, 0.14 * len(reasons)), 4),
                "reasons_to_distrust": reasons,
                "what_would_settle_it": (
                    "Fetch the literature neighbourhood and re-check the gap before "
                    "treating this rank as meaningful."
                    if {"no_literature", "heuristic_scoring"} & flags
                    else "Narrow the operationalization until two readers would agree "
                    "on what counts as an answer."
                ),
            }
        )
    reviewed.sort(key=lambda r: (-r["doubt_score"], r["question_id"]))
    return {
        "most_suspect_first": reviewed,
        "note": (
            "Ordered by how much reason there is to distrust each item — the "
            "inverse of the curiosity ranking, deliberately. Nothing here says a "
            "question is bad; it says what you have not yet checked."
        ),
    }


# --- safety ---------------------------------------------------------------------------


def _lens_safety(items: Sequence[RankedQuestion]) -> dict[str, Any]:
    """Surface what could cause harm, ordered by risk rather than value."""
    flagged = []
    for item in items:
        flags = _flags(item)
        dual_use = sorted(f for f in flags if "dual_use" in f or "risk" in f or "review" in f)
        needs_review = bool(dual_use) or item.scores.risk >= 0.5
        flagged.append(
            {
                "question_id": item.question.id,
                "question": item.question.question,
                "risk_axis": round(float(item.scores.risk), 4),
                "impact_axis": round(float(item.scores.impact), 4),
                "flags": dual_use,
                "needs_human_review": needs_review,
                "why": (
                    "Elevated risk axis and/or dual-use flags."
                    if needs_review
                    else "No risk flags on this item."
                ),
            }
        )
    flagged.sort(key=lambda r: (-r["risk_axis"], r["question_id"]))
    review_count = sum(1 for f in flagged if f["needs_human_review"])
    return {
        "by_risk": flagged,
        "needing_review": review_count,
        "checklist": [
            "Name who bears the cost if this line is pursued and goes wrong.",
            "Confirm the ValueProfile max_risk actually reflects that exposure.",
            "For anything flagged, record the review decision alongside the result.",
            "Do not publish an actionable protocol for a flagged item without review.",
        ],
        "note": (
            "Heuristic risk filter, not a biosecurity authority. Absence of a flag "
            "is not clearance."
        ),
    }


# --- focus ----------------------------------------------------------------------------


def _lens_focus(items: Sequence[RankedQuestion]) -> dict[str, Any]:
    """Stop widening. Take the single best target and go down."""
    from artificial_emotions.decompose import decompose_ranked

    target = items[0]
    plan = decompose_ranked(target, depth=3)
    return {
        "target": {
            "question_id": target.question.id,
            "question": target.question.question,
            "curiosity_score": target.curiosity_score,
        },
        "investigation_plan": plan,
        "set_aside": [
            {"question_id": i.question.id, "question": i.question.question} for i in items[1:]
        ],
        "note": (
            "Everything but the target is set aside on purpose. Breadth is what "
            "the curiosity loop is for; this is the opposite move."
        ),
    }


# --- close ----------------------------------------------------------------------------


def _lens_close(items: Sequence[RankedQuestion]) -> dict[str, Any]:
    """Decide what to stop doing, and what to write down about it."""
    abandon = []
    for item in items:
        flags = _flags(item)
        reason = None
        if item.gap.status == GapStatus.LIKELY_ANSWERED:
            reason = "the literature appears to have answered this already"
        elif "gate_failed" in flags:
            reason = "it failed the acceptance gates"
        elif item.scores.answerability < 0.4 and item.scores.tractability < 0.45:
            reason = "neither answerable nor tractable as posed"
        elif "near_duplicate_suppressed" in flags:
            reason = "it duplicates something already in the set"
        if reason:
            abandon.append(
                {
                    "question_id": item.question.id,
                    "question": item.question.question,
                    "reason": reason,
                    "null_record": (
                        f"Closed out: {item.question.question} — {reason}. "
                        "Recorded so the next person does not repeat it."
                    ),
                }
            )
    return {
        "stop_doing": abandon,
        "n_to_close": len(abandon),
        "kept": [
            i.question.id for i in items if i.question.id not in {a["question_id"] for a in abandon}
        ],
        "note": (
            "A null result is information. Closing a line and saying why is worth "
            "more than quietly dropping it."
            if abandon
            else "Nothing in this set meets the criteria for closing out."
        ),
    }


# --- taste ----------------------------------------------------------------------------

_VAGUE = ("better", "improve", "optimal", "effective", "good", "useful", "impact of")


def _lens_taste(items: Sequence[RankedQuestion]) -> dict[str, Any]:
    """Critique the *form* of the questions. Says nothing about their value."""
    critiques = []
    for item in items:
        q = item.question.question
        ops = item.question.operationalization or ""
        problems: list[str] = []
        if q.count("?") > 1:
            problems.append("more than one question in one question")
        if q.lower().count(" and ") >= 2:
            problems.append("multiple conjunctions — likely a programme, not a question")
        if len(ops) < 40:
            problems.append("operationalization too short to settle a disagreement")
        if any(v in q.lower() for v in _VAGUE) and len(ops) < 80:
            problems.append("vague comparative with no measurable criterion")
        if len(q.split()) > 30:
            problems.append("long enough that the claim is hard to locate")

        critiques.append(
            {
                "question_id": item.question.id,
                "question": q,
                "well_formed": not problems,
                "problems": problems,
                "form_score": round(max(0.0, 1.0 - 0.2 * len(problems)), 4),
            }
        )
    critiques.sort(key=lambda c: (c["form_score"], c["question_id"]))
    flawed = [c for c in critiques if not c["well_formed"]]
    return {
        "n_with_form_problems": len(flawed),
        "n_reviewed": len(critiques),
        "worst_formed_first": critiques,
        "note": (
            "Form only. A beautifully posed question can be worthless and an ugly "
            "one can be the important one — this stance deliberately cannot tell "
            "you which."
        ),
    }


# --- survey ---------------------------------------------------------------------------


def _lens_survey(items: Sequence[RankedQuestion]) -> dict[str, Any]:
    """Map who already occupies this ground."""
    rows = []
    for item in items:
        works = item.gap.related_works or []
        citations = [float(h.cited_by_count or 0) for h in works]
        mean_cites = sum(citations) / len(citations) if citations else 0.0
        if not works:
            crowding = "unmapped"
            advice = "No neighbours retrieved — either genuinely open or badly queried."
        elif len(works) >= 6 and mean_cites >= 100:
            crowding = "crowded"
            advice = "Well-occupied and well-cited. Differentiate sharply or collaborate."
        elif len(works) >= 6:
            crowding = "active"
            advice = "Active but not dominated. Read before proposing."
        else:
            crowding = "sparse"
            advice = "Few neighbours. Check the query before assuming novelty."
        rows.append(
            {
                "question_id": item.question.id,
                "question": item.question.question,
                "related_works": len(works),
                "mean_citations": round(mean_cites, 1),
                "crowding": crowding,
                "advice": advice,
                "titles": [h.title for h in works[:3]],
            }
        )
    rows.sort(key=lambda r: (-r["related_works"], r["question_id"]))
    return {
        "by_crowding": rows,
        "note": (
            "Density of retrieved neighbours, not a bibliometric analysis. Sparse "
            "here means sparse in what was retrieved — it is not proof of novelty."
        ),
    }


# --- wonder ---------------------------------------------------------------------------


def _lens_wonder(items: Sequence[RankedQuestion]) -> dict[str, Any]:
    """What is most *surprising* here, setting aside whether it is valuable.

    The curiosity ranking is ValueProfile-weighted: it answers "what best serves
    the values you stated". This asks the orthogonal question — what would most
    change your picture if you looked. A question can be top of one list and
    bottom of the other, and the difference is the interesting part.
    """
    rows = []
    for item in items:
        pull = 0.6 * item.scores.surprise + 0.4 * item.scores.neglectedness
        rank_gap = None
        rows.append(
            {
                "question_id": item.question.id,
                "question": item.question.question,
                "surprise_axis": round(float(item.scores.surprise), 4),
                "neglectedness_axis": round(float(item.scores.neglectedness), 4),
                "novelty_pull": round(float(pull), 4),
                "rank_by_curiosity": item.rank,
                "rank_gap": rank_gap,
            }
        )
    rows.sort(key=lambda r: (-r["novelty_pull"], r["question_id"]))
    for position, row in enumerate(rows, start=1):
        if row["rank_by_curiosity"]:
            row["rank_gap"] = int(row["rank_by_curiosity"]) - position

    moved = [r for r in rows if r["rank_gap"] not in (None, 0)]
    return {
        "by_novelty_pull": rows,
        "disagrees_with_curiosity_on": len(moved),
        "note": (
            "Ranked by surprise and neglectedness only — the ValueProfile is "
            "deliberately ignored here. A large rank_gap means your values and "
            "your sense of novelty disagree about that item, which is usually "
            "worth a second look either way."
        ),
    }


STANCES: dict[str, Stance] = {
    s.name: s
    for s in (
        Stance(
            name="doubt",
            asks="Which of these am I most likely to be wrong about?",
            use_when="Before you act on a ranking, or before you show it to someone.",
            driving_emotions=(
                "skepticism",
                "suspicion",
                "hubris",
                "humility",
                "doubt",
                "pride",
                "shame",
            ),
            lens=_lens_doubt,
        ),
        Stance(
            name="safety",
            asks="Which of these could hurt someone, and who reviews it?",
            use_when="Any set touching dual-use, clinical, or deployment territory.",
            driving_emotions=("anxiety", "reluctance", "compassion", "fear", "disgust"),
            lens=_lens_safety,
        ),
        Stance(
            name="focus",
            asks="If I could only pursue one, what exactly would I do first?",
            use_when="You have decided. You want a plan, not more options.",
            driving_emotions=(
                "absorption",
                "determination",
                "persistence",
                "conviction",
                "joy",
            ),
            lens=_lens_focus,
        ),
        Stance(
            name="close",
            asks="What should we stop doing, and what should we write down about it?",
            use_when="End of a sprint, or when a line has stopped paying.",
            driving_emotions=(
                "disappointment",
                "resignation",
                "satisfaction",
                "sadness",
                "anger",
            ),
            lens=_lens_close,
        ),
        Stance(
            name="taste",
            asks="Which of these are badly posed, regardless of whether they matter?",
            use_when="Editing a proposal, or triaging questions someone else wrote.",
            driving_emotions=("elegance", "parsimony", "dissonance", "clarity"),
            lens=_lens_taste,
        ),
        Stance(
            name="wonder",
            asks="What is most surprising here, regardless of whether it is valuable?",
            use_when="You want to be surprised rather than to optimise. Also a check "
            "on whether your ValueProfile is filtering out the interesting things.",
            driving_emotions=(
                "wonder",
                "surprise",
                "insight",
                "interest",
                "enjoyment",
                "uncertainty",
                "awe",
                "sublimity",
                "intrigue",
            ),
            lens=_lens_wonder,
        ),
        Stance(
            name="survey",
            asks="Who already owns this ground?",
            use_when="Before committing effort, to avoid duplicating live work.",
            driving_emotions=(
                "respect",
                "envy",
                "recognition",
                "trust",
                "admiration",
                "gratitude",
            ),
            lens=_lens_survey,
        ),
    )
}


def list_stances() -> dict[str, Any]:
    """Describe every stance — what it asks and when to reach for it."""
    return {
        "count": len(STANCES),
        "stances": [s.describe() for s in STANCES.values()],
        "note": (
            "Curiosity answers 'what is worth investigating'. These answer the "
            "other questions, and each is the wrong tool for the others' job."
        ),
    }


def apply_stance(name: str, items: Sequence[RankedQuestion]) -> dict[str, Any]:
    """View a ranked set through one stance.

    Raises:
        CuriosityError: if ``name`` is not a known stance.
    """
    from artificial_emotions.errors import ERR_VALIDATION, CuriosityError

    key = (name or "").strip().lower()
    stance = STANCES.get(key)
    if stance is None:
        raise CuriosityError(
            ERR_VALIDATION,
            f"Unknown stance '{name}'. Known: {', '.join(sorted(STANCES))}",
            details={"known": sorted(STANCES)},
        )
    if not items:
        return {
            **stance.describe(),
            "n_items": 0,
            "view": {},
            "note": "Nothing to look at — the run returned no rankable items.",
        }

    return {
        **stance.describe(),
        "n_items": len(items),
        "view": stance.lens(items),
        "honesty": "stance_view_only",
        "claims_not": [
            "a re-ranking — the ValueProfile ordering you were given is unchanged",
            "an answer to any question in the set",
            "authority in the stance's domain (safety, bibliometrics, editing)",
        ],
    }
