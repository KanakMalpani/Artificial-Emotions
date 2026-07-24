"""EIG-inspired idea-graph export — debug/display only (no silent re-rank).

research/EIG_IDEATION_GRAPHS.md
"""

from __future__ import annotations

from typing import Any

from artificial_curiosity.diversity import jaccard


def export_idea_graph(
    candidates: list[dict[str, Any]],
    *,
    similarity_threshold: float = 0.28,
    conflict_tag_pairs: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    """
    Build a tiny graph: nodes = questions, edges = similarity | conflict.

    Conflict edges are optional profile/tag heuristics (e.g. risk vs basic_science).
    Does **not** change ranks or scores.
    """
    nodes: list[dict[str, Any]] = []
    for i, row in enumerate(candidates):
        qid = str(row.get("question_id") or row.get("id") or f"n{i}")
        nodes.append(
            {
                "id": qid,
                "question": str(row.get("question") or "")[:400],
                "rank": row.get("rank"),
                "curiosity_score": row.get("curiosity_score"),
                "gap_status": row.get("gap_status"),
                "tags": list(row.get("tags") or []),
                "answerability": (row.get("axes") or {}).get("answerability")
                if isinstance(row.get("axes"), dict)
                else row.get("answerability"),
            }
        )

    edges: list[dict[str, Any]] = []
    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            a, b = nodes[i], nodes[j]
            sim = jaccard(a["question"], b["question"])
            if sim >= similarity_threshold:
                edges.append(
                    {
                        "source": a["id"],
                        "target": b["id"],
                        "type": "similarity",
                        "weight": round(float(sim), 4),
                    }
                )
            tags_a = {str(t).lower() for t in (a.get("tags") or [])}
            tags_b = {str(t).lower() for t in (b.get("tags") or [])}
            pairs = conflict_tag_pairs or [
                ("dual_use", "public"),
                ("weapons", "open_science"),
            ]
            for ta, tb in pairs:
                if (ta in tags_a and tb in tags_b) or (tb in tags_a and ta in tags_b):
                    edges.append(
                        {
                            "source": a["id"],
                            "target": b["id"],
                            "type": "conflict",
                            "weight": 1.0,
                            "note": f"tag conflict {ta}/{tb}",
                        }
                    )

    return {
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "nodes": nodes,
        "edges": edges,
        "similarity_threshold": similarity_threshold,
        "changes_ranks": False,
        "honesty": (
            "EIG-inspired debug idea graph — display only. Similarity ≠ support; "
            "conflict edges are coarse tag heuristics. Does not replace verify+rank "
            "or ValueProfile. See research/EIG_IDEATION_GRAPHS.md."
        ),
        "docs": "research/EIG_IDEATION_GRAPHS.md",
    }
