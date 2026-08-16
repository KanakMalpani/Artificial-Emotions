"""Stable ``explore`` import vs domain-jump / dual-use-drop split.

``explore.py`` remains the public path. Jump order and clusters are unchanged.
``drop_dual_use_for_step`` still omits only ``dual_use_high``. Heuristic residual
stays residual — not a biosafety oracle.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from artificial_emotions import explore, explore_domains, explore_drop
from artificial_emotions.cli_pkg.commands import explore as explore_cmd
from artificial_emotions.cli_pkg.commands import ranking
from artificial_emotions.explore import (
    _CLUSTERS,
    _JUMP_ORDER,
    _domain_cluster,
    _next_domain,
    drop_dual_use_for_step,
)
from artificial_emotions.explore_drop import drop_dual_use_for_step as drop_impl


def test_explore_reexports_domain_helpers():
    assert explore._domain_cluster is explore_domains._domain_cluster
    assert explore._next_domain is explore_domains._next_domain
    assert explore._resolve_jump is explore_domains._resolve_jump
    assert explore.domains is explore_domains.domains
    assert explore._CLUSTERS is explore_domains._CLUSTERS
    assert explore._JUMP_ORDER is explore_domains._JUMP_ORDER
    assert callable(explore.explore)


def test_explore_reexports_dual_use_drop():
    assert explore.drop_dual_use_for_step is drop_impl
    assert drop_dual_use_for_step is explore_drop.drop_dual_use_for_step


def test_jump_order_and_clusters_unchanged():
    assert _JUMP_ORDER["ai"] == "biology"
    assert _JUMP_ORDER["energy"] == "physics"
    assert _JUMP_ORDER["social"] == "ai"
    assert frozenset({"biology", "medicine"}) in _CLUSTERS
    assert frozenset({"physics", "materials", "energy"}) in _CLUSTERS
    assert frozenset({"climate", "energy"}) in _CLUSTERS
    assert frozenset({"ai", "social"}) in _CLUSTERS
    assert _domain_cluster("energy") == frozenset({"physics", "materials", "energy", "climate"})
    assert _next_domain("ai", [], forbid_similar=True) == "biology"


def test_drop_dual_use_for_step_only_omits_dual_use_high():
    hot = SimpleNamespace(question=SimpleNamespace(id="hot"), flags=["dual_use_high"])
    review = SimpleNamespace(question=SimpleNamespace(id="review"), flags=["human_review_risk"])
    plain = SimpleNamespace(question=SimpleNamespace(id="plain"), flags=[])
    items = [hot, review, plain]

    same, none = drop_dual_use_for_step(items, enabled=False)
    assert same is items
    assert none == []

    kept, dropped_ids = drop_dual_use_for_step(items, enabled=True)
    assert dropped_ids == ["hot"]
    assert kept == [review, plain]
    assert all("dual_use_high" not in (item.flags or []) for item in kept)


def test_drop_all_dual_use_high_keeps_empty_list():
    only = SimpleNamespace(question=SimpleNamespace(id="only"), flags=["dual_use_high"])
    kept, dropped_ids = drop_dual_use_for_step([only], enabled=True)
    assert kept == []
    assert dropped_ids == ["only"]


def test_cli_explore_handler_is_reexported_from_ranking():
    assert ranking._explore is explore_cmd._explore
    assert "_explore" in ranking.__all__
    assert explore_cmd.__all__ == ["_explore"]


def test_scars_shares_explore_domains_jump_order():
    """Single jump-order dict; scars must not import explore.py (cycle)."""
    from artificial_emotions import scars

    assert scars._JUMP_ORDER is explore_domains._JUMP_ORDER
    nxt, bias = scars.next_domain_biased("ai", [], scars=[], affinities=[])
    assert nxt == _next_domain("ai", [], forbid_similar=False)
    assert bias is None
    src = Path(scars.__file__).read_text(encoding="utf-8")
    assert "from artificial_emotions.explore import" not in src
    assert "import artificial_emotions.explore\n" not in src
