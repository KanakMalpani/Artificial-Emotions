"""Affect copy honesty: inner_monologue is computational, not experiential first-person.

Does not weaken mcp_lint FORBIDDEN_PHRASES — this is a dedicated payload check.
The word ``ambivalence`` is allowed (and required on high-tension mixes).
"""

from __future__ import annotations

import pytest

from artificial_emotions.emotions import feel, mix_emotions
from artificial_emotions.mcp_lint import FORBIDDEN_PHRASES

# Experiential first-person — not the word "ambivalence", not "does not feel".
_BANNED_EXPERIENTIAL = ("i feel", "i register", "i am pulled")


def _monologue(weights: dict[str, float]) -> str:
    return str(mix_emotions(weights)["felt_simulation"]["inner_monologue"])


@pytest.mark.parametrize(
    "weights",
    [
        {"curiosity": 40, "confusion": 30, "awe": 30},
        {"conviction": 45, "doubt": 40, "urgency": 15},
        {"curiosity": 50, "boredom": 50},
        {"conviction": 50, "doubt": 50},
        {"conviction": 100},
        {"boredom": 100},
        {"joy": 50, "trust": 50},
        {"curiosity": 34, "skepticism": 33, "humility": 33},
    ],
)
def test_inner_monologue_is_computational_not_experiential(weights: dict[str, float]) -> None:
    felt = mix_emotions(weights)["felt_simulation"]
    assert felt["computational_only"] is True
    assert felt["mode"] == "computational_affect"
    mono = felt["inner_monologue"]
    lowered = mono.lower()
    for phrase in _BANNED_EXPERIENTIAL:
        assert phrase not in lowered, f"{phrase!r} leaked into inner_monologue: {mono}"
    assert "computational affect" in lowered or "computational_affect" in lowered
    assert "does not feel" in lowered
    assert "as_close_to_feeling_as_possible" not in felt


def test_high_tension_names_ambivalence_without_first_person() -> None:
    mono = _monologue({"curiosity": 50, "boredom": 50})
    lowered = mono.lower()
    assert "ambivalence" in lowered
    assert "do not collapse the mix" in lowered
    for phrase in _BANNED_EXPERIENTIAL:
        assert phrase not in lowered
    # Copy test must not ban the word ambivalence.
    assert "ambivalence" not in {p.lower() for p in _BANNED_EXPERIENTIAL}


def test_feel_alias_uses_computational_copy() -> None:
    out = feel(curiosity=50, awe=50)
    felt = out["felt_simulation"]
    assert felt["computational_only"] is True
    lowered = felt["inner_monologue"].lower()
    assert "computational affect" in lowered
    assert "does not feel" in lowered
    for phrase in _BANNED_EXPERIENTIAL:
        assert phrase not in lowered


def test_copy_lint_does_not_weaken_mcp_forbidden_phrases() -> None:
    """Guard: this file adds a copy test; it must not shrink the MCP phrase table."""
    for phrase in (
        "always use",
        "you must",
        "emotion recognition",
        "guaranteed breakthrough",
        "feels curiosity",
    ):
        assert phrase in FORBIDDEN_PHRASES
