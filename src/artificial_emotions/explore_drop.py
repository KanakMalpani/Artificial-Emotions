"""Explore-step dual-use omission.

Callers import from ``artificial_emotions.explore`` (stable). When the
modulation plan sets ``drop_dual_use``, this omits items flagged
``dual_use_high`` only. ``human_review_risk`` is kept. Empty kept lists are
allowed; replacements are not invented.

The classifier remains a weighted heuristic with residual evasion — not a
biosafety oracle and not dual-use solved.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from artificial_emotions.safety import drop_dual_use_items

__all__ = ["drop_dual_use_for_step"]

_T = TypeVar("_T")


def drop_dual_use_for_step(
    items: Sequence[_T],
    *,
    enabled: bool,
) -> tuple[list[_T], list[str]]:
    """Return (kept, dropped_ids) for one explore step.

    When ``enabled`` is false, ``items`` is returned unchanged (same list
    object when already a list). When true, only ``dual_use_high`` is
    dropped via :func:`drop_dual_use_items`.
    """
    if not enabled:
        return items if isinstance(items, list) else list(items), []
    kept, dropped = drop_dual_use_items(items)
    dropped_ids: list[str] = []
    for item in dropped:
        qid = str(getattr(getattr(item, "question", None), "id", "") or "")
        if not qid:
            continue
        dropped_ids.append(qid)
    return kept, dropped_ids
