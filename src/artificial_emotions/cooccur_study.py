"""LitGapFinder-style co-occurrence GapScore — offline study helpers.

research/LITGAP_CORRELATION_STUDY.md — rationale/export only; never silent weight change.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def gap_score(sim: float, cooccur: float) -> float:
    """GapScore = sim * 1/(1+w). Higher ⇒ underexplored high-similarity link."""
    s = max(0.0, min(1.0, float(sim)))
    w = max(0.0, float(cooccur))
    return round(s / (1.0 + w), 6)


def _rankdata(xs: list[float]) -> list[float]:
    """Average ranks for ties (1-based)."""
    n = len(xs)
    order = sorted(range(n), key=lambda i: xs[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def spearman_rho(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 3:
        return None
    rx, ry = _rankdata(xs), _rankdata(ys)
    n = len(xs)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    dy = math.sqrt(sum((b - my) ** 2 for b in ry))
    if dx == 0.0 or dy == 0.0:
        return None
    return round(num / (dx * dy), 4)


def run_cooccur_correlation(
    rows: list[dict[str, Any]] | str | Path,
) -> dict[str, Any]:
    """
    Offline Spearman(GapScore, neglectedness) on fixture rows.

    Each row: {sim, cooccur, neglectedness, optional question_id}.
    """
    if isinstance(rows, (str, Path)):
        data = json.loads(Path(rows).read_text(encoding="utf-8"))
        rows = list(data.get("pairs") or data.get("rows") or [])
    scores: list[float] = []
    neg: list[float] = []
    detail: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        sim = float(raw.get("sim") or raw.get("similarity") or 0.0)
        w = float(raw.get("cooccur") or raw.get("w") or 0.0)
        nval = raw.get("neglectedness")
        if nval is None:
            continue
        gs = gap_score(sim, w)
        scores.append(gs)
        neg.append(float(nval))
        detail.append(
            {
                "question_id": raw.get("question_id"),
                "sim": sim,
                "cooccur": w,
                "gap_score": gs,
                "neglectedness": float(nval),
            }
        )
    rho = spearman_rho(scores, neg)
    return {
        "n": len(detail),
        "spearman_rho": rho,
        "pairs": detail,
        "rationale_key_example": {
            "cooccur_gap": str(detail[0]["gap_score"]) if detail else None,
            "note": "display only — do not feed into neglectedness weight",
        },
        "honesty": (
            "Offline LitGap-style correlation study — not a scorer replacement, "
            "not proof co-occurrence equals ITN neglectedness. See "
            "research/LITGAP_CORRELATION_STUDY.md."
        ),
        "docs": "research/LITGAP_CORRELATION_STUDY.md",
    }


def cooccur_rationale_key(sim: float, cooccur: float) -> dict[str, str]:
    """Optional display-only rationale keys (same pattern as OpenAlex funder keys)."""
    return {
        "cooccur_gap": f"{gap_score(sim, cooccur):.4f}",
        "cooccur_gap_note": "display_only_no_weight_change",
    }
