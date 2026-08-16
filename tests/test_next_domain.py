"""Jump helper: `_next_domain` with optional similar-domain forbid.

Helpers live in ``explore_domains``; this file still imports from ``explore``.
"""

from __future__ import annotations

from artificial_emotions.explore import _domain_cluster, _next_domain, _resolve_jump

# Walk from ai until social would be the first unvisited hop.
_AI_UNTIL_SOCIAL = [
    "biology",
    "materials",
    "climate",
    "energy",
    "physics",
    "medicine",
    "ai",
]

# Walk from biology until medicine would be the first unvisited hop.
_BIOLOGY_UNTIL_MEDICINE = [
    "materials",
    "climate",
    "energy",
    "physics",
    "social",
    "ai",
    "biology",
]


def test_without_forbid_jump_order_unchanged():
    assert _next_domain("ai", []) == "biology"
    assert _next_domain("ai", [], forbid_similar=False) == "biology"


def test_forbid_from_ai_does_not_land_on_social():
    assert _next_domain("ai", _AI_UNTIL_SOCIAL) == "social"
    nxt = _next_domain("ai", _AI_UNTIL_SOCIAL, forbid_similar=True)
    assert nxt != "social"
    assert nxt == "ai"


def test_forbid_from_biology_does_not_land_on_medicine():
    assert _next_domain("biology", _BIOLOGY_UNTIL_MEDICINE) == "medicine"
    nxt = _next_domain("biology", _BIOLOGY_UNTIL_MEDICINE, forbid_similar=True)
    assert nxt != "medicine"
    assert nxt == "biology"


def test_forbid_still_takes_dissimilar_default_hop():
    assert _next_domain("ai", [], forbid_similar=True) == "biology"
    assert _next_domain("biology", [], forbid_similar=True) == "materials"


def test_energy_cluster_covers_physical_and_earth():
    cluster = _domain_cluster("energy")
    assert cluster == frozenset({"physics", "materials", "energy", "climate"})
    assert _next_domain("energy", []) == "physics"
    assert _next_domain("energy", [], forbid_similar=True) == "medicine"


def test_resolve_jump_without_forbid_lands_on_social():
    nxt, bias, skipped = _resolve_jump(
        "ai",
        _AI_UNTIL_SOCIAL,
        forbid_similar=False,
        mem_scars=[],
        mem_affinities=[],
    )
    assert nxt == "social"
    assert bias is None
    assert skipped is False


def test_resolve_jump_forbid_skips_similar_and_stays():
    nxt, bias, skipped = _resolve_jump(
        "ai",
        _AI_UNTIL_SOCIAL,
        forbid_similar=True,
        mem_scars=[],
        mem_affinities=[],
    )
    assert nxt == "ai"
    assert nxt != "social"
    assert bias is None
    assert skipped is True
