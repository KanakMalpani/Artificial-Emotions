"""A6 Avoidance detection — repeated non-selection, never motive claims.

Guards from docs/PLAN_ALIVE.md Track A6 / alive multiagent plan.
"""

from __future__ import annotations

from artificial_emotions.avoidance import (
    CANNOT_DISTINGUISH_NOTE,
    MIN_ENCOUNTERS_FOR_AVOIDANCE,
    apply_avoidance_to_feeling,
    avoidance_monologue,
    avoiding_payload,
    detect_avoidance,
)
from artificial_emotions.memory import PersistentMemory


def test_avoidance_requires_real_repeated_encounters() -> None:
    """No crying wolf on one sighting — threshold must be real and repeated."""
    assert MIN_ENCOUNTERS_FOR_AVOIDANCE >= 6

    # One encounter, never picked — must not flag.
    assert detect_avoidance({"ai-04": 1}, {}) == []
    assert detect_avoidance({"ai-04": 1}, {"ai-04": 0}) == []

    # A handful under the floor — still quiet.
    under = MIN_ENCOUNTERS_FOR_AVOIDANCE - 1
    assert under >= 1
    assert detect_avoidance({"ai-04": under}, {}) == []

    # Exactly at the floor with zero selections — flags.
    patterns = detect_avoidance({"ai-04": MIN_ENCOUNTERS_FOR_AVOIDANCE}, {})
    assert len(patterns) == 1
    assert patterns[0].question_id == "ai-04"
    assert patterns[0].encounters == MIN_ENCOUNTERS_FOR_AVOIDANCE
    assert patterns[0].selections == 0

    # Seen enough but actually picked — not avoidance.
    assert (
        detect_avoidance(
            {"ai-04": MIN_ENCOUNTERS_FOR_AVOIDANCE},
            {"ai-04": 1},
        )
        == []
    )

    # Caller cannot lower the effective floor to a single sighting.
    assert detect_avoidance({"ai-04": 1}, {}, min_encounters=1) == []

    # Memory path: six sessions that only encounter, never select as best.
    mem = PersistentMemory()
    for i in range(MIN_ENCOUNTERS_FOR_AVOIDANCE):
        mem.record_session(
            domain="ai",
            session_id=f"s{i}",
            question_ids=["ai-04", "other"],
            best_question_id="other",
        )
    assert mem.encounters["ai-04"] == MIN_ENCOUNTERS_FOR_AVOIDANCE
    assert mem.selections.get("ai-04", 0) == 0
    assert mem.selections.get("other", 0) == MIN_ENCOUNTERS_FOR_AVOIDANCE
    flagged = detect_avoidance(mem.encounters, mem.selections)
    assert [p.question_id for p in flagged] == ["ai-04"]

    payload = avoiding_payload(encounters=mem.encounters, selections=mem.selections)
    assert payload["count"] == 1
    assert payload["min_encounters"] == MIN_ENCOUNTERS_FOR_AVOIDANCE


def test_avoidance_is_not_claimed_as_a_motive() -> None:
    """Reports the pattern; explicitly cannot distinguish avoidance from judgment."""
    patterns = detect_avoidance(
        {"ai-04": MIN_ENCOUNTERS_FOR_AVOIDANCE},
        {},
    )
    assert patterns
    mono = avoidance_monologue(patterns)
    lowered = mono.lower()

    assert "ai-04" in mono
    assert str(MIN_ENCOUNTERS_FOR_AVOIDANCE) in mono
    assert "zero" in lowered or "0 times" in lowered
    assert CANNOT_DISTINGUISH_NOTE in mono
    assert "either good judgment or avoidance" in lowered
    assert "can't tell which" in lowered or "cannot tell which" in lowered

    # Must not mind-read.
    forbidden = (
        "i am avoiding",
        "i avoid because",
        "motivated by",
        "fear of",
        "i feel",
        "phenomenal",
        "because i am afraid",
        "reluctance caused",
    )
    for phrase in forbidden:
        assert phrase not in lowered, f"motive/phenomenal claim leaked: {phrase!r}"

    payload = avoiding_payload(
        encounters={"ai-04": MIN_ENCOUNTERS_FOR_AVOIDANCE},
        selections={},
    )
    assert payload["honesty"] == "pattern_not_motive"
    claims = " ".join(payload["claims_not"]).lower()
    assert "motive" in claims
    assert "judgment" in claims
    assert "phenomenal" in claims
    assert payload["cannot_distinguish"] == CANNOT_DISTINGUISH_NOTE

    for item in payload["avoiding"]:
        assert "cannot_distinguish" in item
        assert "motive" in " ".join(item["claims_not"]).lower()

    feeling = apply_avoidance_to_feeling(
        {
            "inner_monologue": "Computational affect: primary=curiosity. Honesty: computational_affect; does not feel.",
            "not_claimed": ["biological emotion"],
        },
        patterns,
    )
    assert feeling is not None
    feeling_text = feeling["inner_monologue"].lower()
    assert "either good judgment or avoidance" in feeling_text
    assert "i am avoiding" not in feeling_text
    assert any("motive" in t for t in feeling["not_claimed"])
    assert any("phenomenal" in t for t in feeling["not_claimed"])
