"""Form-only critique of investigation briefs / operationalizations.

Does **not** change ranks or scores. Flags sprawl, missing falsifier, anthropomorphism,
and invented-citation tells — research/CRITIC_DEBATE_JUDGES.md.
"""

from __future__ import annotations

import re
from typing import Any

_AND_OR_SPLIT = re.compile(r"\b(?:and|or|;)\b", re.I)
_FALSIFIER = re.compile(
    r"falsif|discriminating|would refute|stopping rule|reduce confidence|disconfirm",
    re.I,
)
_ANTHRO = re.compile(
    r"\b(?:feels? curiosity|the ai is curious|detects? (?:your )?emotions?|"
    r"emotion recognition|is curious about)\b",
    re.I,
)
_CITATION_CLAIM = re.compile(
    r"\b(?:we prove|definitively shows|settled by|cited in Nature|"
    r"everyone knows)\b",
    re.I,
)


def critique_brief(
    *,
    question: str = "",
    operationalization: str = "",
    brief: str = "",
    why_it_matters: str = "",
) -> dict[str, Any]:
    """Return form issues only — never mutates scores or ranks."""
    issues: list[dict[str, str]] = []
    ops = (operationalization or "").strip()
    brief_t = (brief or "").strip()
    q = (question or "").strip()
    blob = " ".join([q, ops, brief_t, why_it_matters or ""])

    # F9-ish sprawl: multiple questions / conjunction pile-up in ops or question
    q_marks = q.count("?")
    if q_marks >= 2:
        issues.append(
            {
                "code": "sprawl_multi_question",
                "severity": "warn",
                "detail": "Question text contains multiple '?' — prefer one focal unknown.",
            }
        )
    if ops and len(_AND_OR_SPLIT.findall(ops)) >= 3 and len(ops) > 160:
        issues.append(
            {
                "code": "sprawl_ops",
                "severity": "warn",
                "detail": (
                    "Operationalization piles many conjunctions — may be several "
                    "questions in one (F9)."
                ),
            }
        )

    if ops and not _FALSIFIER.search(ops + " " + brief_t):
        issues.append(
            {
                "code": "missing_falsifier",
                "severity": "info",
                "detail": (
                    "No clear falsifier / discriminating observation phrasing in ops or brief."
                ),
            }
        )

    if _ANTHRO.search(blob):
        issues.append(
            {
                "code": "anthropomorphism",
                "severity": "warn",
                "detail": "Anthropomorphic / ERS-like phrasing — strip before publish.",
            }
        )

    if _CITATION_CLAIM.search(blob):
        issues.append(
            {
                "code": "overclaim_settled",
                "severity": "warn",
                "detail": ("Language sounds settled/overclaimed without gap-status evidence."),
            }
        )

    if brief_t and "related" in brief_t.lower() and "answered" in brief_t.lower():
        # ok — often includes honesty
        pass
    elif brief_t and "gap status" not in brief_t.lower() and "gap=" not in brief_t.lower():
        if brief_t.startswith("##"):
            issues.append(
                {
                    "code": "brief_missing_gap_cue",
                    "severity": "info",
                    "detail": "Brief may omit explicit gap-status reminder.",
                }
            )

    return {
        "ok": True,
        "n_issues": len(issues),
        "issues": issues,
        "changes_ranks": False,
        "honesty": (
            "Form-only critic — does not re-rank, rewrite scores, or strip dual-use risk. "
            "See research/CRITIC_DEBATE_JUDGES.md."
        ),
    }
