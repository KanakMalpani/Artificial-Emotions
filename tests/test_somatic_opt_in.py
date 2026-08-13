"""Somatic search knobs are opt-in; appraisal mixes still hit mix_intensity_cap.

Wave 1 CapAndOptIn: fear-heavy appraisal cannot panic-widen search without
``--somatic-modulate`` / ``CuriosityConfig.somatic_modulate``. Opt-in still
cannot raise the risk ceiling. ``tighten_safety`` / ``drop_dual_use`` may
always apply. Catalog ``coercion: ""`` is unset, not ``low``.
"""

from __future__ import annotations

import inspect

from artificial_emotions.appraisal import AppraisalSignal
from artificial_emotions.cli import build_parser
from artificial_emotions.emotions import emotion_catalog
from artificial_emotions.explore import explore
from artificial_emotions.models import CuriosityConfig, ValueProfile
from artificial_emotions.modulate import (
    ALWAYS_ON_HIGH_COERCION_EFFECTS,
    HIGH_COERCION_IDS,
    high_coercion_effect_allowed,
    modulate_config,
    somatic_modulate_requested,
)


def _fear_heavy_signals(*_args, **_kwargs) -> list[AppraisalSignal]:
    return [
        AppraisalSignal(
            emotion="fear",
            weight=0.9,
            because="high max_risk with low tractability",
            evidence={"max_risk": 0.95, "mean_tractability": 0.1},
        ),
    ]


def test_high_coercion_ids_are_the_somatic_cluster():
    assert HIGH_COERCION_IDS == frozenset({"fear", "anger", "disgust", "joy", "sadness"})
    high = {
        str(e["id"])
        for e in emotion_catalog()["emotions"]
        if str(e.get("coercion") or "") == "high"
    }
    assert HIGH_COERCION_IDS == high


def test_empty_coercion_is_unset_not_low():
    """Placeholder ``coercion: ""`` does not grant low-coercion search knobs."""
    assert (
        high_coercion_effect_allowed(
            "widen_search", somatic_modulate=False, emotion_id="fear", coercion=""
        )
        is False
    )
    assert (
        high_coercion_effect_allowed(
            "widen_search", somatic_modulate=False, emotion_id="curiosity", coercion=""
        )
        is True
    )


def test_mix_containing_high_coercion_ids_counts_as_asking():
    assert somatic_modulate_requested(mix_weights={"fear": 0.4, "curiosity": 0.6}) is True
    assert somatic_modulate_requested(mix_weights={"curiosity": 0.8}) is False
    assert somatic_modulate_requested(somatic_modulate=True, mix_weights={"curiosity": 1.0}) is True
    # Appraisal dumps are not a request — explore passes from_appraisal via False flag.
    assert somatic_modulate_requested(mix_weights={"anger": 0.9}, from_appraisal=True) is False


def test_direct_modulate_mix_with_fear_counts_as_asking():
    _cfg, plan = modulate_config(CuriosityConfig(domain="ai"), {"fear": 0.9})
    assert plan.somatic_modulate is True
    _cfg, forced_off = modulate_config(
        CuriosityConfig(domain="ai"), {"fear": 0.9}, somatic_modulate=False
    )
    assert forced_off.somatic_modulate is False


def test_high_coercion_search_effects_need_opt_in_safety_does_not():
    assert ALWAYS_ON_HIGH_COERCION_EFFECTS == frozenset({"tighten_safety", "drop_dual_use"})
    assert high_coercion_effect_allowed("tighten_safety", somatic_modulate=False, emotion_id="fear")
    assert high_coercion_effect_allowed(
        "drop_dual_use", somatic_modulate=False, emotion_id="disgust"
    )
    assert high_coercion_effect_allowed("surface_only", somatic_modulate=False, emotion_id="joy")
    assert not high_coercion_effect_allowed(
        "widen_search", somatic_modulate=False, emotion_id="fear", coercion="high"
    )
    assert high_coercion_effect_allowed(
        "widen_search", somatic_modulate=True, emotion_id="fear", coercion="high"
    )
    assert not high_coercion_effect_allowed(
        "narrow_search", somatic_modulate=False, emotion_id="sadness"
    )


def test_curiosity_config_somatic_modulate_defaults_off():
    assert CuriosityConfig().somatic_modulate is False


def test_cli_somatic_modulate_flag():
    parser = build_parser()
    assert parser.parse_args(["explore"]).somatic_modulate is False
    assert parser.parse_args(["explore", "--somatic-modulate"]).somatic_modulate is True


def test_explore_wires_mix_cap_and_explicit_somatic_flag():
    source = inspect.getsource(explore)
    assert "mix_intensity_cap=float(profile.mix_intensity_cap)" in source
    assert "somatic_modulate=bool(config.somatic_modulate)" in source
    assert "somatic_modulate" in inspect.signature(explore).parameters
    assert "somatic_modulate" in inspect.signature(modulate_config).parameters


def test_explore_passes_profile_mix_intensity_cap(monkeypatch):
    captured: dict[str, object] = {}
    from artificial_emotions.emotions import mix_emotions as real_mix

    def wrap(weights, **kwargs):
        captured["kwargs"] = kwargs
        captured["weights"] = dict(weights)
        return real_mix(weights, **kwargs)

    monkeypatch.setattr("artificial_emotions.explore.appraise_run", _fear_heavy_signals)
    monkeypatch.setattr("artificial_emotions.explore.mix_emotions", wrap)
    out = explore(
        domain="ai",
        steps=1,
        n_return=3,
        profile_name="public_demo_strict_risk",
        allow_domain_jump=False,
    )
    assert captured["kwargs"]["mix_intensity_cap"] == 0.35
    mix = out["final_mix"]
    assert mix["mix_intensity_cap"] == 0.35
    assert mix["intensity_capped"] is True
    assert out["somatic_modulate"] is False


def test_fear_heavy_appraisal_does_not_panic_widen_without_opt_in(monkeypatch):
    monkeypatch.setattr("artificial_emotions.explore.appraise_run", _fear_heavy_signals)
    out = explore(
        domain="ai",
        steps=2,
        n_return=4,
        n_candidates=16,
        allow_domain_jump=False,
        somatic_modulate=False,
    )
    assert out["somatic_modulate"] is False
    for step in out["trajectory"]["steps"]:
        for change in step["modulation"]:
            if change["knob"] == "n_candidates":
                assert float(change["after"]) <= float(change["before"])
                assert change["driver"] != "fear"
            if "max_risk" in str(change["knob"]):
                assert float(change["after"]) <= float(change["before"])


def test_somatic_opt_in_still_cannot_raise_risk_ceiling(monkeypatch):
    monkeypatch.setattr("artificial_emotions.explore.appraise_run", _fear_heavy_signals)
    out = explore(
        domain="ai",
        steps=2,
        n_return=4,
        n_candidates=16,
        profile_name="public_demo_strict_risk",
        allow_domain_jump=False,
        somatic_modulate=True,
    )
    assert out["somatic_modulate"] is True
    assert out["value_profile"]["max_risk"] == 0.55
    for step in out["trajectory"]["steps"]:
        for change in step["modulation"]:
            if "max_risk" in str(change["knob"]):
                assert float(change["after"]) <= float(change["before"])
    cfg = CuriosityConfig(
        domain="ai",
        use_literature=False,
        somatic_modulate=True,
        value_profile=ValueProfile(max_risk=0.5),
    )
    new, plan = modulate_config(cfg, {"fear": 0.9, "anger": 0.4}, somatic_modulate=True)
    assert plan.somatic_modulate is True
    assert new.value_profile.max_risk <= 0.5


def test_anxiety_may_tighten_risk_without_somatic_opt_in():
    config = CuriosityConfig(domain="ai", use_literature=False, somatic_modulate=False)
    new, plan = modulate_config(config, {"anxiety": 0.8}, somatic_modulate=False)
    assert plan.somatic_modulate is False
    assert new.value_profile.max_risk < config.value_profile.max_risk
