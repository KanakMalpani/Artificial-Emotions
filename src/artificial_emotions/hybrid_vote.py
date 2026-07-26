"""HybridQuestion-inspired offline vote — form/heuristic proxy only.

research/HYBRID_VOTE_OFFLINE.md — never silent re-rank; not multi-LLM in CI.
"""

from __future__ import annotations

from typing import Any

from artificial_emotions.critique import critique_brief
from artificial_emotions.hivemind import top_n_pairwise_similarity


def _heuristic_vote(row: dict[str, Any]) -> dict[str, Any]:
    """Keep / drop / rewrite from form critic + length (offline stand-in for LLM vote)."""
    q = str(row.get("question") or "")
    ops = str(row.get("operationalization") or "")
    brief = str(row.get("brief") or "")
    critique = critique_brief(
        question=q,
        operationalization=ops,
        brief=brief,
        why_it_matters=str(row.get("why_it_matters") or ""),
    )
    codes = {i["code"] for i in critique.get("issues") or []}
    if "sprawl_multi_question" in codes or "anthropomorphism" in codes:
        decision = "drop"
    elif "missing_falsifier" in codes or "sprawl_ops" in codes:
        decision = "rewrite"
    elif len(q) < 40:
        decision = "rewrite"
    else:
        decision = "keep"
    return {
        "question_id": row.get("question_id") or row.get("id"),
        "decision": decision,
        "issue_codes": sorted(codes),
        "n_issues": critique.get("n_issues"),
    }


def cross_model_vote(
    candidates: list[dict[str, Any]],
    *,
    judges: int = 1,
) -> dict[str, Any]:
    """
    Offline vote annotations over candidate unknowns.

    ``judges``>1 only repeats the same form heuristic (CI-safe). Live multi-model
    vote is out of scope for default pytest — see research/HYBRID_VOTE_OFFLINE.md.
    """
    votes = []
    for row in candidates:
        ballots = [_heuristic_vote(row) for _ in range(max(1, int(judges)))]
        # Majority of identical heuristics — same decision; kept for API shape
        decision = ballots[0]["decision"]
        votes.append({**ballots[0], "n_judges": len(ballots), "decision": decision})

    keep = sum(1 for v in votes if v["decision"] == "keep")
    drop = sum(1 for v in votes if v["decision"] == "drop")
    rewrite = sum(1 for v in votes if v["decision"] == "rewrite")
    n = len(votes) or 1
    texts = [str(c.get("question") or "") for c in candidates]
    hive = top_n_pairwise_similarity(texts)

    return {
        "n_candidates": len(candidates),
        "votes": votes,
        "keep_rate": round(keep / n, 4),
        "drop_rate": round(drop / n, 4),
        "rewrite_rate": round(rewrite / n, 4),
        "hivemind_similarity": hive,
        "changes_ranks": False,
        "honesty": (
            "Offline form/heuristic vote proxy — not multi-LLM HybridQuestion "
            "reproduction, not VOI, and never silently re-ranks. Agreement ≠ truth. "
            "See research/HYBRID_VOTE_OFFLINE.md."
        ),
        "docs": "research/HYBRID_VOTE_OFFLINE.md",
    }
