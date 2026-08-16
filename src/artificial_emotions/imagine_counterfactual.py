"""Counterfactual imagination generator (twin of wonder).

Callers import from ``artificial_emotions.imagine_lenses`` (stable) or
``artificial_emotions.imagine`` (public registry). Offline — uses only
``related_works`` already on the ranked item. Never scores confidence.
Does not invent a new kind.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from artificial_emotions.decompose import decompose_question, key_terms
from artificial_emotions.imagine_quarantine import ImaginedContent
from artificial_emotions.models import GapStatus, LiteratureHit, RankedQuestion

__all__ = [
    "_generate_counterfactual",
]

_YES_NO_LEAD = re.compile(
    r"^\s*(does|do|is|are|can|could|will|would|should)\b",
    re.IGNORECASE,
)
_WHICH_LEAD = re.compile(r"^\s*(which|what)\b", re.IGNORECASE)
_THRESHOLD_IN_TEXT = re.compile(
    r"([A-Za-z][A-Za-z0-9 _\-]{0,28}?)\s*"
    r"(>=|<=|≥|≤|>|<|=)\s*"
    r"(-?\d+(?:\.\d+)?)\s*(%)?"
)
_NEG_FINDING = re.compile(
    r"\b("
    r"fail(?:s|ed|ure)?|null|no\s+effect|below|under|did\s+not|"
    r"cannot|unable|negative\s+result|contradict"
    r")\b",
    re.IGNORECASE,
)


def _posit_answers(item: RankedQuestion) -> list[str]:
    """Invent a small set of plausible answers from question form (deterministic)."""
    q = (item.question.question or "").strip()
    ops = (item.question.operationalization or "").strip()
    answers: list[str] = []

    if _YES_NO_LEAD.match(q):
        answers.append("yes — the claimed effect / condition holds as posed")
        answers.append("no — the claimed effect / condition does not hold")
    elif _WHICH_LEAD.match(q):
        answers.append("a single dominant answer exists among the candidates")
        answers.append("no single candidate dominates — the ranking is flat")
    else:
        answers.append("the operationalization succeeds under its stated criteria")
        answers.append("the operationalization fails under its stated criteria")

    for assumption in list(item.question.assumptions or [])[:2]:
        a = (assumption or "").strip()
        if a:
            answers.append(f"assuming {a}")

    # Always keep the operationalization-as-answer as a checkable posit when present.
    if ops and not any(ops[:40].lower() in a.lower() for a in answers):
        answers.append(f"settled affirmatively under: {ops[:100]}")

    # De-dupe while preserving order; cap so output stays readable.
    seen: set[str] = set()
    out: list[str] = []
    for a in answers:
        key = a.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
        if len(out) >= 4:
            break
    return out


def _consequences_for_answer(
    item: RankedQuestion,
    posited: str,
) -> list[dict[str, str]]:
    """Forward-derive what else must hold if ``posited`` is the answer.

    Reuses ``decompose_question`` falsifiers: each stated criterion becomes a
    consequence that would have to be true; ``refuted_if`` is what literature
    would need to show to contradict it.
    """
    deco = decompose_question(
        item.question,
        depth=1,
        answerability=item.scores.answerability,
        tractability=item.scores.tractability,
        risk=item.scores.risk,
    )
    consequences: list[dict[str, str]] = []
    for falsifier in deco.get("falsifiers") or []:
        criterion = str(falsifier.get("criterion") or "").strip()
        refuted_if = str(falsifier.get("refuted_if") or "").strip()
        if not criterion:
            continue
        consequences.append(
            {
                "consequence": (f"If {posited!r}, then {criterion} must hold"),
                "check_against": refuted_if,
                "source": str(falsifier.get("source") or "falsifier"),
            }
        )

    # Forward step from the discriminating observation.
    step = deco.get("discriminating_step") or {}
    observation = str(step.get("observation") or "").strip()
    if observation:
        consequences.append(
            {
                "consequence": (
                    f"If {posited!r}, then this discriminating observation "
                    f"must be settleable: {observation}"
                ),
                "check_against": (
                    "existing work already settles that observation with a "
                    "null or contradictory result"
                ),
                "source": "discriminating_step",
            }
        )
    return consequences


def _work_blob(hit: LiteratureHit) -> str:
    return f"{hit.title or ''} {hit.abstract_snippet or ''}".strip()


def _threshold_contradicted_by_text(ops: str, blob: str) -> bool:
    """True when literature text reports a flipped / failed threshold from ops."""
    matches = _THRESHOLD_IN_TEXT.findall(ops or "")
    if not matches:
        return False
    blob_l = blob.lower()
    for metric, op, value, pct in matches:
        words = [w for w in metric.strip().strip("-—:,").split() if w]
        metric_clean = " ".join(words[-3:]).lower() if words else ""
        if not metric_clean:
            continue
        # Metric mentioned + negative finding language near a numeric claim.
        if metric_clean.split()[0] not in blob_l and metric_clean not in blob_l:
            # Allow last token (e.g. "auroc") alone.
            last = words[-1].lower() if words else ""
            if last and last not in blob_l:
                continue
        if _NEG_FINDING.search(blob):
            return True
        # Explicit flipped comparison in the abstract (e.g. "AUROC = 0.55").
        for m2, _op2, val2, _pct2 in _THRESHOLD_IN_TEXT.findall(blob):
            m2_words = [w for w in m2.strip().split() if w]
            m2_last = (m2_words[-1] if m2_words else "").lower()
            metric_last = (words[-1] if words else "").lower()
            if m2_last and metric_last and m2_last == metric_last:
                try:
                    reported = float(val2)
                    target = float(value)
                except ValueError:
                    continue
                if op in (">=", "≥", ">") and reported < target:
                    return True
                if op in ("<=", "≤", "<") and reported > target:
                    return True
                if pct and reported != target and _NEG_FINDING.search(blob):
                    return True
    return False


def _literature_contradicts(
    item: RankedQuestion,
    consequence: dict[str, str],
) -> list[str]:
    """Return titles of related works that contradict this consequence."""
    works = list(item.gap.related_works or [])
    if not works:
        return []

    check = (consequence.get("check_against") or "").lower()
    cons = (consequence.get("consequence") or "").lower()
    ops = item.question.operationalization or ""
    flagged: list[str] = []

    # Falsifier: "genuinely unanswered" is contradicted when literature already
    # settles the gap.
    gap_settled = item.gap.status == GapStatus.LIKELY_ANSWERED or (
        item.gap.strong_match_count >= 2 and item.gap.top_overlap >= 0.5
    )
    if gap_settled and (
        "genuinely unanswered" in cons
        or "pre-registered replication already reports" in check
        or "already reports the effect" in check
    ):
        flagged.extend(w.title for w in works if w.title)

    check_terms = set(key_terms(consequence.get("check_against") or "", limit=8))
    cons_terms = set(key_terms(consequence.get("consequence") or "", limit=8))
    target_terms = check_terms | cons_terms

    for hit in works:
        blob = _work_blob(hit)
        if not blob:
            continue
        blob_l = blob.lower()
        title = hit.title or "untitled"

        if _threshold_contradicted_by_text(ops, blob):
            if title not in flagged:
                flagged.append(title)
            continue

        # Negative finding language + shared terms with the check/consequence.
        work_terms = set(key_terms(blob, limit=12))
        overlap = target_terms & work_terms
        if len(overlap) >= 2 and _NEG_FINDING.search(blob):
            if title not in flagged:
                flagged.append(title)
            continue

        # Explicit "null" / "fail" abstracts that share the main metric token.
        if _NEG_FINDING.search(blob) and any(t in blob_l for t in cons_terms if len(t) > 4):
            if title not in flagged:
                flagged.append(title)

    return flagged[:5]


def _cheapest_check(
    consequences: list[dict[str, str]],
    contradictions: dict[str, list[str]],
    *,
    tractability: float,
) -> str:
    """Pick the cheapest consequence to check — prefer uncontradicted, then any."""
    cost = "low" if tractability >= 0.6 else "medium" if tractability >= 0.4 else "high"
    uncontradicted = [c for c in consequences if not contradictions.get(c["consequence"])]
    pool = uncontradicted or list(consequences)
    if not pool:
        return f"(none derived; cost band {cost})"
    # Prefer operationalization / measurement-sourced checks — usually cheaper.
    preferred = next(
        (
            c
            for c in pool
            if c.get("source") in ("operationalization", "measurement", "discriminating_step")
        ),
        pool[0],
    )
    return (
        f"{preferred['consequence']} "
        f"[expected cost band: {cost}; check: {preferred['check_against']}]"
    )


def _generate_counterfactual(items: Sequence[RankedQuestion]) -> list[ImaginedContent]:
    """Posit answers, forward-derive consequences, flag literature contradictions.

    Twin of the wonder stance. Offline — uses only ``related_works`` already on
    the ranked item (fixture / prior retrieval). Never scores confidence.
    """
    out: list[ImaginedContent] = []
    for item in items:
        for posited in _posit_answers(item):
            consequences = _consequences_for_answer(item, posited)
            contradictions: dict[str, list[str]] = {}
            for cons in consequences:
                hits = _literature_contradicts(item, cons)
                if hits:
                    contradictions[cons["consequence"]] = hits

            invented: list[str] = [f"posited_answer: {posited}"]
            for cons in consequences:
                invented.append(f"consequence: {cons['consequence']}")
                titles = contradictions.get(cons["consequence"]) or []
                for title in titles:
                    invented.append(f"literature_contradicts: {title!r} ↔ {cons['consequence']}")

            cheapest = _cheapest_check(
                consequences,
                contradictions,
                tractability=float(item.scores.tractability),
            )
            invented.append(f"cheapest_to_check: {cheapest}")

            if not item.gap.related_works:
                invented.append(
                    "literature_check: no related_works on this item — "
                    "contradictions unchecked against the corpus"
                )

            contradicted_bits = []
            for cons_text, titles in contradictions.items():
                contradicted_bits.append(f"{cons_text} — contradicted by: {'; '.join(titles)}")
            contradicted_section = (
                "; ".join(contradicted_bits)
                if contradicted_bits
                else "none flagged against related_works on this item"
            )

            content = (
                f"Counterfactual — suppose the answer to "
                f"{item.question.question!r} is: {posited}. "
                f"Implied consequences: "
                f"{'; '.join(c['consequence'] for c in consequences) or '(none)'}. "
                f"Existing literature contradictions: {contradicted_section}. "
                f"Cheapest to check: {cheapest}."
            )

            grounded = [item.question.id]
            for titles in contradictions.values():
                for t in titles:
                    if t not in grounded:
                        grounded.append(t)

            out.append(
                ImaginedContent(
                    content=content,
                    kind="counterfactual",
                    driven_by=("wonder", "surprise", "insight"),
                    grounded_in=tuple(grounded),
                    invented=tuple(invented),
                )
            )
    return out
