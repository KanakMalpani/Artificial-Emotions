"""A5 Temperament — presets diverge trajectories; default explore stays identical."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artificial_emotions.appraisal import appraise_run
from artificial_emotions.explore import explore
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.temperament import (
    PRESET_NAMES,
    PRESETS,
    BaselineMood,
    Temperament,
    apply_to_config,
    ensure_default_file,
    load_temperament,
    resolve_temperament,
    scale_appraisal_signals,
)


@pytest.fixture(scope="module")
def ranked():
    return CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=5)
    ).run()


def _trajectory_fingerprint(result: dict) -> tuple:
    """Measurable trajectory signature — feelings, picks, knobs, appraisal mass."""
    steps = result["trajectory"]["steps"]
    feelings = tuple(s["primary_feeling"] for s in steps)
    picks = tuple(s.get("top_question_id") for s in steps)
    domains = tuple(s.get("domain") for s in steps)
    appraisal_mass = tuple(
        round(sum(float(a["weight"]) for a in s.get("appraisal") or []), 4) for s in steps
    )
    top_emotions = tuple(
        tuple(
            sorted(
                (a["emotion"], round(float(a["weight"]), 3)) for a in (s.get("appraisal") or [])[:4]
            )
        )
        for s in steps
    )
    temp = result.get("temperament") or {}
    biases = tuple(
        (b.get("knob"), b.get("before"), b.get("after")) for b in (temp.get("biases") or [])
    )
    risk = None
    for b in temp.get("biases") or []:
        if b.get("knob") == "value_profile.max_risk":
            risk = b.get("after")
    return (feelings, picks, domains, appraisal_mass, top_emotions, biases, risk)


def test_presets_produce_measurably_different_trajectories() -> None:
    """Same corpus / seed — named presets must leave visibly different paths."""
    results = {
        name: explore(
            domain="ai",
            steps=3,
            n_return=3,
            seed=42,
            temperament=name,
        )
        for name in PRESET_NAMES
    }

    fingerprints = {name: _trajectory_fingerprint(r) for name, r in results.items()}

    # Every preset discloses itself.
    for name, result in results.items():
        assert "temperament" in result
        assert result["temperament"]["temperament"]["name"] == name
        assert "does not feel" in result["temperament"]["temperament"]["honesty"]

    # At least three distinct trajectories across four presets.
    unique = set(fingerprints.values())
    assert len(unique) >= 3, (
        f"presets did not diverge enough: { {k: fingerprints[k][:3] for k in fingerprints} }"
    )

    # Cautious vs restless: risk aversion and novelty must diverge on knobs.
    cautious_bias = {b["knob"]: b for b in results["cautious"]["temperament"]["biases"]}
    restless_bias = {b["knob"]: b for b in results["restless"]["temperament"]["biases"]}
    assert "value_profile.max_risk" in cautious_bias
    assert (
        cautious_bias["value_profile.max_risk"]["after"]
        < cautious_bias["value_profile.max_risk"]["before"]
    )
    assert "n_candidates" in restless_bias
    assert restless_bias["n_candidates"]["after"] > restless_bias["n_candidates"]["before"]
    assert cautious_bias["value_profile.max_risk"]["after"] < (
        restless_bias.get("value_profile.max_risk", {}).get("after")
        or results["restless"]["value_profile"]["max_risk"]
    )

    # Dogged vs flighty: appraisal mass / primary path differs (reactivity + recovery).
    assert fingerprints["dogged"] != fingerprints["flighty"]

    # Pairwise: cautious must differ from restless on the fingerprint.
    assert fingerprints["cautious"] != fingerprints["restless"]


def test_default_explore_is_unchanged_without_temperament() -> None:
    """temperament=None keeps today's payload (NO_MEMORY / fresh-install invariant)."""
    a = explore(domain="ai", steps=2, n_return=3, seed=42)
    b = explore(domain="ai", steps=2, n_return=3, seed=42, temperament=None)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    assert "temperament" not in a


def test_temperament_never_loosens_max_risk() -> None:
    config = CuriosityConfig(domain="ai", use_llm=False, use_literature=False)
    before = float(config.value_profile.max_risk)
    # Even a "reckless" novelty-high / risk-low preset must not raise the ceiling.
    reckless = Temperament(
        name="reckless_custom",
        risk_aversion=0.0,
        novelty_seeking=1.0,
        reactivity=1.0,
    )
    after_cfg, apps = apply_to_config(config, reckless)
    assert float(after_cfg.value_profile.max_risk) <= before
    assert not any(
        a.knob == "value_profile.max_risk" and float(a.after) > float(a.before) for a in apps
    )

    tight = Temperament(name="tight", risk_aversion=1.0)
    tight_cfg, tight_apps = apply_to_config(config, tight)
    assert float(tight_cfg.value_profile.max_risk) < before
    assert any(a.knob == "value_profile.max_risk" for a in tight_apps)


def test_temperament_scales_supported_signals_only(ranked) -> None:
    base = appraise_run(ranked)
    # Fabrication guard: frustration needs dead ends — temperament must not invent it.
    restless = PRESETS["restless"]
    scaled = appraise_run(ranked, steps_without_progress=0, temperament=restless)
    assert "frustration" not in {s.emotion for s in scaled}

    with_support = appraise_run(ranked, steps_without_progress=3, temperament=restless)
    assert "frustration" in {s.emotion for s in with_support}

    # Reactivity > 0.5 amplifies total mass vs unscaled.
    cautious = PRESETS["cautious"]
    high = scale_appraisal_signals(list(base), restless)
    low = scale_appraisal_signals(list(base), cautious)
    assert sum(s.weight for s in high) > sum(s.weight for s in low)


def test_temperament_toml_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "temperament.toml"
    ensure_default_file(path)
    text = path.read_text(encoding="utf-8")
    assert "baseline_mood" in text
    assert "reactivity" in text
    assert "recovery_rate" in text
    assert "skepticism_bias" in text
    assert "novelty_seeking" in text
    assert "risk_aversion" in text

    loaded = load_temperament(path)
    assert loaded.name == "custom"
    assert loaded.reactivity == pytest.approx(0.7)
    assert loaded.baseline_mood.valence == pytest.approx(0.1)

    # resolve custom loads the file.
    resolved = resolve_temperament("custom", path=path)
    assert resolved is not None
    assert resolved.novelty_seeking == pytest.approx(0.8)

    # Neutral temperament resolves to None (no-op).
    assert resolve_temperament(Temperament(name="custom")) is None


def test_all_presets_are_registered() -> None:
    assert set(PRESET_NAMES) == {"restless", "cautious", "dogged", "flighty"}
    for name in PRESET_NAMES:
        assert PRESETS[name].baseline_mood == BaselineMood(
            valence=PRESETS[name].baseline_mood.valence,
            arousal=PRESETS[name].baseline_mood.arousal,
            dominance=PRESETS[name].baseline_mood.dominance,
        )
