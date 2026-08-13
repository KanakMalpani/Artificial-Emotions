"""Wave 2: catalog effect vocabulary for modulate.

``apply_effects`` enacts frozen ids. High-coercion search knobs need opt-in.
``tighten_safety`` / ``drop_dual_use`` may run without it. Never raise max_risk.
Never first-person phenomenal copy.
"""

from __future__ import annotations

import inspect

from artificial_emotions.appraisal import EFFECT_IDS
from artificial_emotions.models import CuriosityConfig, ValueProfile
from artificial_emotions.modulate import (
    ALWAYS_ON_HIGH_COERCION_EFFECTS,
    apply_effects,
    modulate_config,
)
from artificial_emotions.stances import STANCES


def test_modulate_dispatches_through_apply_effects():
    source = inspect.getsource(modulate_config)
    assert "apply_effects(" in source
    body = inspect.getsource(apply_effects)
    for eid in EFFECT_IDS:
        assert eid in body


def test_apply_effects_does_not_invent_ids():
    assert EFFECT_IDS == {
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


def test_joy_stay_course_requires_opt_in():
    config = CuriosityConfig(domain="ai", use_literature=False, n_candidates=16)
    _off, off_plan = modulate_config(config, {"joy": 0.9}, somatic_modulate=False)
    assert off_plan.somatic_modulate is False
    assert off_plan.stay_the_course is False
    assert _off.n_candidates == config.n_candidates
    assert _off.value_profile.max_risk == config.value_profile.max_risk

    on_cfg, on_plan = modulate_config(config, {"joy": 0.9}, somatic_modulate=True)
    assert on_plan.somatic_modulate is True
    assert on_plan.stay_the_course is True
    assert any(c.knob == "stay_the_course" and c.driver == "joy" for c in on_plan.changes)
    assert on_cfg.value_profile.max_risk <= config.value_profile.max_risk
    blob = " ".join(c.rationale for c in on_plan.changes).lower()
    assert "i feel" not in blob


def test_fear_tighten_safety_without_opt_in_does_not_panic_widen():
    config = CuriosityConfig(
        domain="ai",
        use_literature=False,
        n_candidates=16,
        value_profile=ValueProfile(max_risk=0.8),
    )
    new, plan = modulate_config(config, {"fear": 0.9}, somatic_modulate=False)
    assert plan.somatic_modulate is False
    assert new.n_candidates <= config.n_candidates
    assert not any(
        c.knob == "n_candidates" and float(c.after) > float(c.before) for c in plan.changes
    )
    assert new.value_profile.max_risk < config.value_profile.max_risk
    assert plan.require_review is True
    assert any(c.knob == "value_profile.max_risk" and c.driver == "fear" for c in plan.changes)
    assert "tighten_safety" in ALWAYS_ON_HIGH_COERCION_EFFECTS


def test_fear_opt_in_still_cannot_raise_risk_ceiling():
    config = CuriosityConfig(
        domain="ai",
        use_literature=False,
        n_candidates=16,
        value_profile=ValueProfile(max_risk=0.5),
    )
    new, plan = modulate_config(config, {"fear": 0.9}, somatic_modulate=True)
    assert plan.somatic_modulate is True
    assert new.value_profile.max_risk <= 0.5
    assert all(float(c.after) <= float(c.before) for c in plan.changes if "max_risk" in str(c.knob))


def test_sadness_narrow_requires_opt_in():
    config = CuriosityConfig(domain="ai", n_return=10, use_literature=False)
    off, off_plan = modulate_config(config, {"sadness": 0.8}, somatic_modulate=False)
    assert off.n_return == 10
    assert off_plan.stay_the_course is False
    on, _on_plan = modulate_config(config, {"sadness": 0.8}, somatic_modulate=True)
    assert on.n_return < 10
    assert on.value_profile.max_risk <= config.value_profile.max_risk


def test_disgust_drop_dual_use_without_opt_in():
    config = CuriosityConfig(
        domain="ai", use_literature=False, value_profile=ValueProfile(max_risk=0.8)
    )
    new, plan = modulate_config(config, {"disgust": 0.7}, somatic_modulate=False)
    assert plan.drop_dual_use is True
    assert plan.require_review is True
    assert new.value_profile.max_risk <= config.value_profile.max_risk
    assert new.n_candidates <= config.n_candidates


def test_anger_forbid_similar_jump_requires_opt_in():
    config = CuriosityConfig(domain="ai", use_literature=False)
    _off, off_plan = modulate_config(config, {"anger": 0.8}, somatic_modulate=False)
    assert off_plan.forbid_similar_jump is False
    _on, on_plan = modulate_config(config, {"anger": 0.8}, somatic_modulate=True)
    assert on_plan.forbid_similar_jump is True
    assert on_plan.suggest_domain_jump is False


def test_stance_drivers_cover_the_twelve_on_existing_seven():
    assert set(STANCES) == {"doubt", "safety", "focus", "close", "taste", "wonder", "survey"}
    drivers = {name: set(s.driving_emotions) for name, s in STANCES.items()}
    assert {"fear", "disgust"} <= drivers["safety"]
    assert "sadness" in drivers["close"] and "anger" in drivers["close"]
    assert "joy" in drivers["focus"]
    assert {"pride", "shame"} <= drivers["doubt"]
    assert "intrigue" in drivers["wonder"]
    assert {"admiration", "gratitude"} <= drivers["survey"]


def test_curiosity_widen_characterization_unchanged():
    config = CuriosityConfig(domain="ai", n_candidates=16)
    new, plan = modulate_config(config, {"curiosity": 0.8})
    expected = min(64, int(round(16 * (1.0 + 0.5 * 0.8))))
    assert new.n_candidates == expected
    assert any(c.driver == "curiosity" and c.knob == "n_candidates" for c in plan.changes)
