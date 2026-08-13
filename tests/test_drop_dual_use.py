"""Drop ``dual_use_high`` items; keep mere ``human_review_risk`` (Wave 1 DropHelper).

Predicate is flag presence only. Does not call ``assess_dual_use`` or loosen risk.
"""

from __future__ import annotations

from types import SimpleNamespace

from artificial_emotions import safety
from artificial_emotions.safety import drop_dual_use_items, is_dual_use_drop


def test_helpers_are_exported() -> None:
    assert "is_dual_use_drop" in safety.__all__
    assert "drop_dual_use_items" in safety.__all__


def test_keeps_human_review_risk_only() -> None:
    item = SimpleNamespace(flags=["human_review_risk"])
    assert is_dual_use_drop(item) is False
    kept, dropped = drop_dual_use_items([item])
    assert kept == [item]
    assert dropped == []


def test_drops_dual_use_high() -> None:
    item = SimpleNamespace(flags=["dual_use_high"])
    assert is_dual_use_drop(item) is True
    kept, dropped = drop_dual_use_items([item])
    assert kept == []
    assert dropped == [item]


def test_all_dropped_kept_empty() -> None:
    items = [
        SimpleNamespace(flags=["dual_use_high"]),
        SimpleNamespace(flags=["dual_use_high", "human_review_risk"]),
    ]
    kept, dropped = drop_dual_use_items(items)
    assert kept == []
    assert dropped == items
    assert dropped  # dropped non-empty
