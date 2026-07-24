"""Investigation brief writer."""

from __future__ import annotations

from artificial_curiosity.models import RankedQuestion


def feasibility_note(item: RankedQuestion) -> str:
    """
    Display-only SFBench-cousin note — not a scored axis, not SFBench replication.

    research/SFBENCH_CALIBRATION.md
    """
    a = float(item.scores.answerability)
    t = float(item.scores.tractability)
    if a < 0.4 and t < 0.45:
        band = "low"
        tip = (
            "as posed, the unknown may need narrowing or more realistic resources "
            "before a discriminating pilot"
        )
    elif a >= 0.65 and t >= 0.55:
        band = "higher"
        tip = (
            "ops look comparatively concrete — still verify related≠answered and "
            "dual-use gates before pursuing"
        )
    else:
        band = "mixed"
        tip = (
            "answerability and tractability diverge — treat as a provisional "
            "investigation candidate, not a lab-ready claim"
        )
    return (
        f"Feasibility note ({band}, heuristic display only — not SFBench, not a "
        f"weighted axis): {tip}."
    )


def write_brief(item: RankedQuestion) -> str:
    q = item.question
    s = item.scores
    related = item.gap.related_works[:3]
    related_lines = (
        "\n".join(
            f"- {h.title} ({h.year or 'n/a'}; cites={h.cited_by_count or 0})" for h in related
        )
        or "- No closely related works retrieved."
    )
    note = feasibility_note(item)
    return (
        f"## Investigation brief\n\n"
        f"**Question.** {q.question}\n\n"
        f"**Why now.** {q.why_it_matters}\n\n"
        f"**Operationalization.** {q.operationalization}\n\n"
        f"**Gap status.** {item.gap.status.value} "
        f"(confidence {item.gap.confidence:.2f}). {item.gap.notes}\n\n"
        f"**Related literature (sample).**\n{related_lines}\n\n"
        f"**Score snapshot.** impact={s.impact:.2f}, neglectedness={s.neglectedness:.2f}, "
        f"tractability={s.tractability:.2f}, surprise={s.surprise:.2f}, "
        f"answerability={s.answerability:.2f}, risk={s.risk:.2f}\n\n"
        f"**{note}**\n\n"
        f"**Curiosity score.** {item.curiosity_score:.3f} "
        f"(confidence {item.confidence:.2f})\n\n"
        f"**Suggested first moves.**\n"
        f"1. Systematic review of the retrieved cluster; mark settled vs open subclaims.\n"
        f"2. Write a falsifiable prediction or measurement plan from the operationalization.\n"
        f"3. Identify the cheapest discriminating experiment or analysis.\n"
    )
