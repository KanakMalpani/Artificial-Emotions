"""Jump helper: `_next_domain` with optional similar-domain forbid.

Calls the helper directly — the explore loop is wired in a later wave.
"""

from __future__ import annotations

from artificial_emotions.explore import _domain_cluster, _next_domain

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
