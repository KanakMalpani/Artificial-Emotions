"""Catalog schema contract for when / effects / use_for / coercion / requires.

Wave 0 freezes key names and vocabularies. Placeholders (empty ``when``,
``effects``, ``use_for``) are allowed; unknown effect ids and unknown
``requires`` tokens are not. Appraisal ``RULES`` behaviour is unchanged.
"""

from __future__ import annotations

import pytest

from artificial_emotions.appraisal import (
    CATALOG_SCHEMA_KEYS,
    CATALOG_WHEN_FEATURES,
    COERCION_LEVELS,
    EFFECT_IDS,
    NEVER_APPRAISE,
    REQUIRES_TOKENS,
    RULES,
    UNBUILT_UNTIL_OUTCOME,
    WHEN_OPS,
    validate_catalog_entry,
    validate_emotion_catalog,
)
from artificial_emotions.emotions import emotion_catalog

_FROZEN_EFFECT_IDS = frozenset(
    {
        "widen_search",
        "narrow_search",
        "demand_literature",
        "decompose",
        "jump_ground",
        "forbid_similar_jump",
        "tighten_safety",
        "drop_dual_use",
        "stay_course",
        "surface_only",
    }
)
_FROZEN_WHEN_OPS = frozenset({"ge", "le", "gt", "lt", "eq", "ne"})
_FROZEN_REQUIRES = frozenset(
    {
        "offline",
        "literature",
        "risk_flags",
        "previous_step",
        "outcome_event",
    }
)
_FROZEN_COERCION = frozenset({"low", "high"})


def _placeholder(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "id": "curiosity",
        "when": [],
        "effects": [],
        "use_for": "",
        "coercion": "",
        "requires": [],
    }
    entry.update(overrides)
    return entry


def test_effect_id_list_is_frozen():
    assert EFFECT_IDS == _FROZEN_EFFECT_IDS


def test_when_ops_coercion_and_requires_are_frozen():
    assert WHEN_OPS == _FROZEN_WHEN_OPS
    assert COERCION_LEVELS == _FROZEN_COERCION
    assert REQUIRES_TOKENS == _FROZEN_REQUIRES


def test_every_catalog_id_has_schema_keys():
    cat = emotion_catalog()
    assert cat["count"] >= 54
    for entry in cat["emotions"]:
        missing = [k for k in CATALOG_SCHEMA_KEYS if k not in entry]
        assert not missing, f"{entry['id']} missing {missing}"


def test_shipped_catalog_passes_schema_validation():
    validate_emotion_catalog()


def test_unknown_effect_id_fails():
    with pytest.raises(ValueError, match="unknown effect"):
        validate_catalog_entry(_placeholder(effects=["not_an_effect"]))


def test_unknown_requires_fails():
    with pytest.raises(ValueError, match="unknown requires"):
        validate_catalog_entry(_placeholder(requires=["not_a_requirement"]))


def test_unknown_requires_string_form_fails():
    with pytest.raises(ValueError, match="unknown requires"):
        validate_catalog_entry(_placeholder(requires="online"))


def test_known_requires_string_form_passes():
    validate_catalog_entry(_placeholder(requires="offline"))


def test_missing_schema_key_fails():
    entry = _placeholder()
    del entry["when"]
    with pytest.raises(ValueError, match="missing catalog schema"):
        validate_catalog_entry(entry)


def test_unknown_when_op_fails():
    with pytest.raises(ValueError, match="unknown when op"):
        validate_catalog_entry(
            _placeholder(when=[{"feature": "gap_ratio", "op": "approx", "value": 0.5}])
        )


def test_unknown_when_feature_fails():
    with pytest.raises(ValueError, match="unknown when feature"):
        validate_catalog_entry(
            _placeholder(when=[{"feature": "not_a_feature", "op": "ge", "value": 0.5}])
        )


def test_unknown_coercion_fails():
    with pytest.raises(ValueError, match="unknown coercion"):
        validate_catalog_entry(_placeholder(coercion="medium"))


def test_empty_placeholders_pass():
    validate_catalog_entry(_placeholder())


def test_valid_when_clause_passes():
    feature = next(iter(sorted(CATALOG_WHEN_FEATURES)))
    validate_catalog_entry(
        _placeholder(
            when=[{"feature": feature, "op": "ge", "value": 0.5}],
            effects=["surface_only"],
            use_for="Surfaces the mix without changing search knobs.",
            coercion="low",
            requires=["offline"],
        )
    )


def test_never_appraise_and_unbuilt_sets_remain():
    """Wave 0 must not delete the named holes; Wave 3 owns that deletion."""
    assert NEVER_APPRAISE
    assert UNBUILT_UNTIL_OUTCOME


_TWELVE_LEFTOVERS = frozenset(
    {
        "anger",
        "fear",
        "joy",
        "sadness",
        "disgust",
        "gratitude",
        "pride",
        "shame",
        "embarrassment",
        "relief",
        "intrigue",
        "admiration",
    }
)


def test_ruled_emotions_have_catalog_when():
    by_id = {e["id"]: e for e in emotion_catalog()["emotions"]}
    missing = [eid for eid in RULES if not by_id[eid]["when"]]
    assert not missing, f"RULES ids still have empty when: {missing}"


def test_twelve_leftovers_keep_empty_when():
    for entry in emotion_catalog()["emotions"]:
        if entry["id"] in _TWELVE_LEFTOVERS:
            assert entry["when"] == [], entry["id"]
            assert entry["effects"] == [], entry["id"]
            assert entry["use_for"] == "", entry["id"]


def test_any_all_and_weight_clauses_validate():
    validate_catalog_entry(
        _placeholder(
            when=[
                {
                    "any": [
                        {"feature": "dual_use_ratio", "op": "gt", "value": 0},
                        {"all": [{"feature": "max_risk", "op": "ge", "value": 0.5}]},
                    ],
                    "weight": ["add", 0.3, ["mul", 0.5, "dual_use_ratio"]],
                }
            ],
            effects=["tighten_safety"],
            use_for="Tighten the risk ceiling when dual-use material is present.",
            coercion="low",
            requires=["risk_flags"],
        )
    )


def test_unknown_weight_op_fails():
    with pytest.raises(ValueError, match="unknown weight op"):
        validate_catalog_entry(_placeholder(when=[{"weight": ["pow", "gap_ratio", 2]}]))
