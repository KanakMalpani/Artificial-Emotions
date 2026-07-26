"""Curiosity depth: turn one ranked unknown into an investigable ladder.

This is the step *past* ranking. Given a question the engine surfaced, it asks
the next layer of questions — what must be measured, what mechanism is implied,
what would confound it, where it stops holding — and names the single
observation that would most split the space.

The invariant that governs every function here: **nothing in the output asserts
an answer.** Each item is a question, a test, a threshold, or a stopping
criterion. A decomposition that concluded something would be a bug, and
``assert_free`` enforces it.

Fully offline and deterministic — no LLM, no network, no keys. The ladder is
built from the question's own text, its stated operationalization, and its score
axes, so the same input always yields the same decomposition.
"""

from __future__ import annotations

import re
from typing import Any

from artificial_emotions.epistemic_cues import (
    TAG_CONFUSION_RISK,
    TAG_CURIOSITY_TARGET,
    TAG_DEAD_END_RISK,
    TAG_INFORMATION_GAP,
    TAG_INSIGHT_CANDIDATE,
    TAG_SCOPE_CREEP_RISK,
)
from artificial_emotions.models import RankedQuestion, UnansweredQuestion

__all__ = [
    "MAX_DEPTH",
    "SUB_QUESTION_KINDS",
    "assert_free",
    "decompose_question",
    "decompose_ranked",
    "key_terms",
]

MAX_DEPTH = 3

# Each kind is a distinct move in narrowing an unknown. Order is the order a
# careful investigator would actually take them in.
SUB_QUESTION_KINDS: tuple[str, ...] = (
    "measurement",
    "baseline",
    "mechanism",
    "confound",
    "boundary",
)

# The subject leads, then the narrowing question. Putting it in a lead-in clause
# rather than mid-sentence keeps the output grammatical whether the subject is a
# noun phrase or a full clause — question text is not reliably either.
_KIND_TEMPLATES: dict[str, dict[str, str]] = {
    "measurement": {
        "template": "{subject} — what observable quantity would make this measurable at all?",
        "why": "An unknown with no defined measurement cannot be resolved, only discussed.",
    },
    "baseline": {
        "template": "{subject} — what does this look like with no intervention (the null case)?",
        "why": "Without a baseline, any observed effect has nothing to be an effect against.",
    },
    "mechanism": {
        "template": "{subject} — which mechanism would have to hold for this to be so?",
        "why": "Naming a candidate mechanism turns a correlation question into a testable one.",
    },
    "confound": {
        "template": "{subject} — what else could produce the same observation?",
        "why": "Listing rivals before measuring is what keeps a positive result meaningful.",
    },
    "boundary": {
        "template": "{subject} — under what conditions does this stop holding?",
        "why": "The edge of a claim is usually cheaper to probe than its centre.",
    },
}

# Children narrow the *parent's move*, not the parent's sentence. Re-parsing a
# generated question produces word salad, so each (parent, child) pair gets its
# own phrasing anchored back to the original subject.
_CHILD_TEMPLATES: dict[tuple[str, str], dict[str, str]] = {
    ("mechanism", "measurement"): {
        "template": "{subject} — what observable quantity would distinguish the candidate mechanisms?",
        "why": "A mechanism you cannot tell apart from its rivals is not yet a hypothesis.",
    },
    ("mechanism", "boundary"): {
        "template": "{subject} — under what conditions would a candidate mechanism fail to hold?",
        "why": "A mechanism that cannot fail anywhere is not making a claim.",
    },
    ("confound", "measurement"): {
        "template": "{subject} — what measurement separates the real effect from its likeliest confound?",
        "why": "Naming the confound is only useful if something distinguishes it.",
    },
    ("confound", "boundary"): {
        "template": "{subject} — where would a confounded result and a real one look identical?",
        "why": "The region where they agree is where a positive result means least.",
    },
}

_KIND_CUES: dict[str, list[str]] = {
    "measurement": [TAG_INFORMATION_GAP, TAG_CURIOSITY_TARGET],
    "baseline": [TAG_INFORMATION_GAP],
    "mechanism": [TAG_INSIGHT_CANDIDATE, TAG_CURIOSITY_TARGET],
    "confound": [TAG_CONFUSION_RISK],
    "boundary": [TAG_CURIOSITY_TARGET],
}

_STOPWORDS = frozenset(
    """
    a an the of to in on for by with and or if is are was were be been being do does did
    what which how why when where who whom whose can could should would will shall may might
    must under over into from at as that this these those it its their there here than then
    most more less least much many any all some each every no not
    """.split()
)

_QUESTION_LEAD = re.compile(
    r"^\s*(what|which|how|why|when|where|who|whose|can|could|does|do|is|are|will|should)\b[\s,]*",
    re.IGNORECASE,
)

# Numeric criteria in an operationalization — the raw material for falsifiers.
_THRESHOLD = re.compile(
    r"([A-Za-z][A-Za-z0-9 _\-]{0,28}?)\s*"
    r"(>=|<=|≥|≤|>|<|=)\s*"
    r"(-?\d+(?:\.\d+)?)\s*(%)?"
)

_FLIP = {">=": "<", "≥": "<", ">": "≤", "<=": ">", "≤": ">", "<": "≥", "=": "≠"}

# Language that would mean the output had stopped asking and started answering.
_ASSERTION_MARKERS = (
    "the answer is",
    "we conclude",
    "this proves",
    "this shows that",
    "therefore the",
    "the cause is",
    "it is because",
    "the mechanism is ",
    "results demonstrate",
)


def key_terms(text: str, *, limit: int = 6) -> list[str]:
    """Content words from a question, in order, de-duplicated."""
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]+", text or "")
    out: list[str] = []
    for w in words:
        lw = w.lower()
        if lw in _STOPWORDS or len(lw) < 3:
            continue
        if lw not in out:
            out.append(lw)
        if len(out) >= limit:
            break
    return out


def _subject_of(question: str) -> str:
    """Strip the interrogative lead so a question can be embedded in a template."""
    body = _QUESTION_LEAD.sub("", (question or "").strip())
    body = body.rstrip("?.! ").strip()
    if not body:
        body = (question or "this unknown").strip().rstrip("?")
    # Keep templates readable rather than swallowing a whole paragraph.
    words = body.split()
    if len(words) > 18:
        body = " ".join(words[:18]) + " …"
    return body[0].lower() + body[1:] if body else body


def _slug(text: str, prefix: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")[:36]
    return f"{prefix}-{s or 'q'}"


def _sub_questions(
    subject: str,
    *,
    parent_id: str,
    depth: int,
    kinds: tuple[str, ...] = SUB_QUESTION_KINDS,
) -> list[dict[str, Any]]:
    """One layer of narrowing over ``subject`` (already stripped of its lead)."""
    out: list[dict[str, Any]] = []
    for kind in kinds:
        spec = _KIND_TEMPLATES[kind]
        node: dict[str, Any] = {
            "id": _slug(f"{kind}-{subject}", parent_id),
            "kind": kind,
            "question": spec["template"].format(subject=subject),
            "why_this_narrows_it": spec["why"],
            "cue_tags": list(_KIND_CUES.get(kind, [])),
            "children": [],
        }
        # Only mechanism and confound reward further splitting; the others bottom
        # out in a single observation and would just generate noise.
        if depth > 1 and kind in ("mechanism", "confound"):
            node["children"] = [
                {
                    "id": _slug(f"{child_kind}-{subject}", node["id"]),
                    "kind": child_kind,
                    "question": _CHILD_TEMPLATES[(kind, child_kind)]["template"].format(
                        subject=subject
                    ),
                    "why_this_narrows_it": _CHILD_TEMPLATES[(kind, child_kind)]["why"],
                    "cue_tags": list(_KIND_CUES.get(child_kind, [])),
                    "narrows": kind,
                    "children": [],
                }
                for child_kind in ("measurement", "boundary")
            ]
        out.append(node)
    return out


def _falsifiers(question: UnansweredQuestion) -> list[dict[str, str]]:
    """Turn stated criteria into the results that would refute them."""
    ops = question.operationalization or ""
    found: list[dict[str, str]] = []
    for metric, op, value, pct in _THRESHOLD.findall(ops):
        # Keep the last few words before the operator — the regex window can pull
        # in prepositional lead-in ("on a held-out cohort with p").
        words = [w for w in metric.strip().strip("-—:,").split() if w]
        while words and words[0].lower() in _STOPWORDS:
            words.pop(0)
        metric_clean = " ".join(words[-3:]) or "the stated metric"
        flipped = _FLIP.get(op, "≠")
        suffix = pct or ""
        found.append(
            {
                "source": "operationalization",
                "criterion": f"{metric_clean} {op} {value}{suffix}",
                "refuted_if": f"{metric_clean} {flipped} {value}{suffix}",
            }
        )
    # Falsifiers that apply regardless of whether a threshold was stated.
    found.append(
        {
            "source": "gap",
            "criterion": "the question is genuinely unanswered",
            "refuted_if": (
                "a pre-registered replication already reports the effect with the "
                "same operationalization"
            ),
        }
    )
    found.append(
        {
            "source": "framing",
            "criterion": "the question is answerable as posed",
            "refuted_if": (
                "no measurement exists that would distinguish the candidate answers from each other"
            ),
        }
    )
    if not question.operationalization or len(question.operationalization) < 40:
        found.append(
            {
                "source": "operationalization",
                "criterion": "success criteria are specified",
                "refuted_if": (
                    "two competent readers would disagree on whether a given result "
                    "counts as answering it"
                ),
            }
        )
    return found


def _discriminating_step(
    question: UnansweredQuestion,
    subs: list[dict[str, Any]],
    *,
    answerability: float | None,
    tractability: float | None,
) -> dict[str, Any]:
    """The one observation to make first, and what it would rule out."""
    a = 0.5 if answerability is None else float(answerability)
    t = 0.5 if tractability is None else float(tractability)

    # A question with no defined measurement must start there regardless of axes.
    weak_ops = len(question.operationalization or "") < 40
    if weak_ops:
        chosen = next((s for s in subs if s["kind"] == "measurement"), subs[0])
        rationale = "No usable success criterion is stated yet, so measurement comes first."
    elif a < 0.45 or t < 0.45:
        chosen = next((s for s in subs if s["kind"] == "boundary"), subs[0])
        rationale = (
            "Answerability or tractability is low — probe the edge of the claim, "
            "which is usually cheaper than its centre."
        )
    else:
        chosen = next((s for s in subs if s["kind"] == "confound"), subs[0])
        rationale = (
            "The question is comparatively well posed, so the highest-value first "
            "move is eliminating rival explanations."
        )

    cost_band = "low" if t >= 0.6 else "medium" if t >= 0.4 else "high"
    return {
        "observation": chosen["question"],
        "from_sub_question": chosen["id"],
        "kind": chosen["kind"],
        "why_this_first": rationale,
        "expected_cost_band": cost_band,
        "what_it_rules_out": (
            "One branch of the space above — record the result either way; a null "
            "here is information, not failure."
        ),
        "honesty": (
            "Selection is a heuristic over stated criteria and score axes. It is not "
            "a computed expected-information-gain and does not claim optimality."
        ),
    }


def _stop_rules(
    *,
    answerability: float | None,
    tractability: float | None,
    risk: float | None,
) -> list[str]:
    rules = [
        "Stop and re-frame if two attempts produce results that rule nothing out.",
        "Stop if the measurement cannot distinguish the candidate answers even in principle.",
    ]
    a = 0.5 if answerability is None else float(answerability)
    t = 0.5 if tractability is None else float(tractability)
    r = 0.0 if risk is None else float(risk)
    if a < 0.45:
        rules.append(
            "Answerability is low: narrow to a single clause before spending "
            "further effort, or close the line out."
        )
    if t < 0.4:
        rules.append(
            "Tractability is low: require a cheap pilot to succeed before "
            "committing to the full investigation."
        )
    if r >= 0.5:
        rules.append(
            "Risk axis is elevated: route through review before any step that "
            "would produce actionable capability, and record that decision."
        )
    return rules


def assert_free(payload: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check the decomposition never states a conclusion.

    The whole surface is meant to deepen a question. This is the guard that
    keeps a template edit from quietly turning it into an answer engine.
    """
    offenders: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]")
        elif isinstance(node, str):
            low = node.lower()
            for marker in _ASSERTION_MARKERS:
                if marker in low:
                    offenders.append(f"{path}: contains {marker!r}")

    walk(payload, "$")
    return (not offenders), offenders


def decompose_question(
    question: UnansweredQuestion,
    *,
    depth: int = 1,
    answerability: float | None = None,
    tractability: float | None = None,
    risk: float | None = None,
) -> dict[str, Any]:
    """Expand one unknown into sub-questions, a first step, and stop rules."""
    depth = max(1, min(int(depth), MAX_DEPTH))
    subject = _subject_of(question.question)
    subs = _sub_questions(subject, parent_id=question.id or "q", depth=depth)

    enabling = list(question.enabling_questions or [])
    # The engine's own ordering: you cannot chase a mechanism you cannot measure.
    enabling += [s["question"] for s in subs if s["kind"] in ("measurement", "baseline")]

    payload: dict[str, Any] = {
        "question_id": question.id,
        "question": question.question,
        "domain": str(question.domain),
        "depth": depth,
        "key_terms": key_terms(question.question),
        "sub_questions": subs,
        "sub_question_count": sum(1 + len(s["children"]) for s in subs),
        "enabling_chain": list(dict.fromkeys(enabling)),
        "discriminating_step": _discriminating_step(
            question, subs, answerability=answerability, tractability=tractability
        ),
        "falsifiers": _falsifiers(question),
        "stop_rules": _stop_rules(
            answerability=answerability, tractability=tractability, risk=risk
        ),
        "open_after_this": (
            "Even if every sub-question above resolves, the original unknown is not "
            "thereby answered — the ladder narrows where to look, it does not close "
            "the gap."
        ),
        "honesty": "decomposition_only",
        "claims_not": [
            "an answer to the question",
            "a hypothesis asserted as true",
            "a computed expected information gain",
            "a guarantee the decomposition is complete",
        ],
        "docs": "docs/EMOTIONS.md",
    }
    ok, offenders = assert_free(payload)
    payload["assertion_free"] = ok
    if not ok:  # pragma: no cover — guard; templates are assertion-free by design
        payload["assertion_offenders"] = offenders
    return payload


def decompose_ranked(item: RankedQuestion, *, depth: int = 1) -> dict[str, Any]:
    """Decompose a ranked result, using its score axes to pick the first step."""
    axes = item.scores
    payload = decompose_question(
        item.question,
        depth=depth,
        answerability=getattr(axes, "answerability", None),
        tractability=getattr(axes, "tractability", None),
        risk=getattr(axes, "risk", None),
    )
    payload["rank"] = item.rank
    payload["curiosity_score"] = item.curiosity_score
    payload["gap_status"] = item.gap.status.value
    payload["inherited_flags"] = list(item.flags or [])
    if str(item.gap.status.value) == "likely_answered":
        payload["stop_rules"].insert(
            0,
            "Gap status is likely_answered — verify the existing result before "
            "decomposing further.",
        )
        payload["sub_questions"] = [s for s in payload["sub_questions"] if s["kind"] != "mechanism"]
        payload["cue_tags_added"] = [TAG_DEAD_END_RISK]
    if len(payload["enabling_chain"]) > 6:
        payload.setdefault("cue_tags_added", []).append(TAG_SCOPE_CREEP_RISK)
    return payload
