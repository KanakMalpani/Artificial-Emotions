"""Offline soundness pass on ranked briefs (ScholarEval/InnoEval cousin).

Display/eval only — never silent re-rank. research/INNOEVAL_JUDGES.md
"""

from __future__ import annotations

from typing import Any

from artificial_curiosity.brief import feasibility_note
from artificial_curiosity.critique import critique_brief
from artificial_curiosity.hivemind import top_n_pairwise_similarity
from artificial_curiosity.models import RankedQuestion


def soundness_pass_item(item: RankedQuestion | dict[str, Any]) -> dict[str, Any]:
    """Form + gap-honesty + feasibility note for one unknown."""
    if isinstance(item, RankedQuestion):
        q = item.question.question
        ops = item.question.operationalization
        brief = item.investigation_brief or ""
        why = item.question.why_it_matters
        qid = item.question.id
        gap = item.gap.status.value
        axes = {
            "answerability": item.scores.answerability,
            "tractability": item.scores.tractability,
            "risk": item.scores.risk,
        }
        feas = feasibility_note(item)
    else:
        q = str(item.get("question") or "")
        ops = str(item.get("operationalization") or "")
        brief = str(item.get("brief") or item.get("investigation_brief") or "")
        why = str(item.get("why_it_matters") or "")
        qid = item.get("question_id") or item.get("id")
        gap = str(item.get("gap_status") or "")
        axes = item.get("axes") if isinstance(item.get("axes"), dict) else {}
        feas = str(item.get("feasibility_note") or "")

    critique = critique_brief(question=q, operationalization=ops, brief=brief, why_it_matters=why)
    gap_ok = "answered" not in gap.lower() or "likely_answered" in gap
    related_honesty = ("related" in brief.lower() and "answered" in brief.lower()) or bool(gap)
    codes = {i["code"] for i in critique.get("issues") or []}
    sound = "pass"
    if "sprawl_multi_question" in codes or "anthropomorphism" in codes:
        sound = "fail"
    elif critique.get("n_issues", 0) >= 2:
        sound = "revise"
    elif not related_honesty and gap_ok:
        sound = "revise"

    return {
        "question_id": qid,
        "gap_status": gap,
        "soundness": sound,
        "critique": critique,
        "feasibility_note": feas,
        "axes_snapshot": {
            "answerability": axes.get("answerability"),
            "tractability": axes.get("tractability"),
            "risk": axes.get("risk"),
        },
        "dimensions": {
            "form_quality": sound != "fail",
            "gap_honesty": related_honesty,
            "falsifier_hint": "missing_falsifier" not in codes,
        },
    }


def soundness_pass(
    candidates: list[RankedQuestion | dict[str, Any]],
) -> dict[str, Any]:
    """Multi-perspective form/gap soundness on top-n — not a consensus science judge."""
    rows = [soundness_pass_item(c) for c in candidates]
    texts = []
    for c in candidates:
        if isinstance(c, RankedQuestion):
            texts.append(c.question.question)
        else:
            texts.append(str(c.get("question") or ""))
    n = len(rows) or 1
    return {
        "n": len(rows),
        "results": rows,
        "pass_rate": round(sum(1 for r in rows if r["soundness"] == "pass") / n, 4),
        "fail_rate": round(sum(1 for r in rows if r["soundness"] == "fail") / n, 4),
        "hivemind_similarity": top_n_pairwise_similarity(texts),
        "changes_ranks": False,
        "honesty": (
            "Offline ScholarEval/InnoEval-cousin soundness pass — form/gap/feasibility "
            "annotations only. Decoupled dimensions; not a global science judge; "
            "never silent re-rank. Profile-scoped values remain separate. "
            "See research/INNOEVAL_JUDGES.md."
        ),
        "docs": "research/INNOEVAL_JUDGES.md",
    }
