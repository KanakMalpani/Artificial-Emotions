"""Stable ``modulate`` import vs ``modulate_effects`` applicators.

Pins re-exports, unknown-id / floor / missing-state guards, curiosity widen
math, always-on ``drop_dual_use`` / ``tighten_safety``, opt-in
``forbid_similar_jump``, and frustration ``jump_ground`` not hopping.
Full catalog characterization stays in ``test_catalog_effects.py``.
"""

from __future__ import annotations

import inspect

from artificial_emotions.appraisal import EFFECT_IDS
from artificial_emotions.models import CuriosityConfig, ValueProfile
from artificial_emotions.modulate import (
    ModulationPlan,
    apply_effects,
    modulate_config,
)
from artificial_emotions.modulate_effects import _EffectState


def _state(
    *,
    config: CuriosityConfig | None = None,
    mix_weights: dict[str, float] | None = None,
) -> _EffectState:
    return _EffectState(
        config=config or CuriosityConfig(domain="ai", n_candidates=16, n_return=10),
        updates={},
        skip=frozenset(),
        exhausted=False,
        mix_weights=mix_weights or {"curiosity": 0.8},
    )


def test_modulate_reexports_effects_without_churn():
    from artificial_emotions import modulate, modulate_effects

    assert modulate.apply_effects is modulate_effects.apply_effects
    assert modulate.ModulationPlan is modulate_effects.ModulationPlan
    assert modulate.ModulationChange is modulate_effects.ModulationChange
    assert modulate.HIGH_COERCION_IDS is modulate_effects.HIGH_COERCION_IDS
    assert modulate.MAX_WEIGHT_DELTA is modulate_effects.MAX_WEIGHT_DELTA
    assert "apply_effects(" in inspect.getsource(modulate_config)


def test_apply_effects_skips_unknown_below_floor_and_missing_state():
    plan = ModulationPlan()
    state = _state()
    apply_effects(
        plan, ("not_an_effect", "widen_search"), 0.05, True, emotion_id="curiosity", state=state
    )
    assert plan.changes == []
    apply_effects(plan, ("not_an_effect",), 0.9, True, emotion_id="curiosity", state=state)
    assert plan.changes == []
    apply_effects(plan, ("widen_search",), 0.9, True, emotion_id="curiosity", state=None)
    assert plan.changes == []
    apply_effects(plan, ("surface_only",), 0.9, True, emotion_id="interest", state=state)
    assert plan.changes == []


def test_apply_effects_enacts_frozen_widen_and_ignores_invented_ids():
    plan = ModulationPlan()
    state = _state()
    apply_effects(
        plan,
        ("invented_panic_widen", "widen_search"),
        0.8,
        True,
        emotion_id="curiosity",
        state=state,
    )
    assert "invented_panic_widen" not in EFFECT_IDS
    assert any(c.knob == "n_candidates" and c.driver == "curiosity" for c in plan.changes)
    assert state.updates["n_candidates"] == min(64, int(round(16 * (1.0 + 0.5 * 0.8))))


def test_apply_effects_drop_dual_use_without_opt_in_forbid_jump_needs_it():
    drop_plan = ModulationPlan()
    apply_effects(
        drop_plan,
        ("drop_dual_use",),
        0.7,
        False,
        emotion_id="disgust",
        coercion="high",
        state=_state(),
    )
    assert drop_plan.drop_dual_use is True
    assert drop_plan.require_review is True

    off = ModulationPlan()
    apply_effects(
        off,
        ("forbid_similar_jump",),
        0.8,
        False,
        emotion_id="anger",
        coercion="high",
        state=_state(),
    )
    assert off.forbid_similar_jump is False

    on = ModulationPlan()
    apply_effects(
        on,
        ("forbid_similar_jump",),
        0.8,
        True,
        emotion_id="anger",
        coercion="high",
        state=_state(),
    )
    assert on.forbid_similar_jump is True


def test_apply_effects_tighten_safety_without_opt_in_never_raises_risk():
    config = CuriosityConfig(
        domain="ai",
        use_literature=False,
        value_profile=ValueProfile(max_risk=0.8),
    )
    state = _state(config=config, mix_weights={"fear": 0.9})
    plan = ModulationPlan()
    apply_effects(
        plan,
        ("tighten_safety",),
        0.9,
        False,
        emotion_id="fear",
        coercion="high",
        state=state,
    )
    after = float(state.updates["value_profile"].max_risk)
    assert after < 0.8
    assert after >= 0.05
    assert plan.require_review is True
    assert all(float(c.after) <= float(c.before) for c in plan.changes if "max_risk" in str(c.knob))


def test_apply_effects_jump_ground_does_not_hop_for_frustration():
    plan = ModulationPlan()
    apply_effects(
        plan,
        ("jump_ground",),
        0.8,
        True,
        emotion_id="frustration",
        state=_state(mix_weights={"frustration": 0.8}),
    )
    assert plan.suggest_domain_jump is False
    assert not any(c.knob == "domain" for c in plan.changes)


def test_plan_assembly_still_owns_modulate_config():
    config = CuriosityConfig(domain="ai", n_candidates=16, use_literature=False)
    new, plan = modulate_config(config, {"curiosity": 0.8})
    assert new.n_candidates > config.n_candidates
    assert plan.weights_touched is False
    assert not any("max_risk" in str(c.knob) for c in plan.changes)
