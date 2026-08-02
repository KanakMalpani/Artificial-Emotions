"""A4 scars and affinities — idiosyncrasy, bounded, disclosed, decaying."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from artificial_emotions.explore import explore
from artificial_emotions.memory import PersistentMemory, memory_disabled
from artificial_emotions.models import CuriosityConfig, resolve_value_profile
from artificial_emotions.modulate import MAX_WEIGHT_DELTA
from artificial_emotions.scars import (
    MAX_AFFINITY_BIAS,
    MAX_SCAR_BIAS,
    MIN_ACTIVE_STRENGTH,
    MIN_HITS_FOR_SCAR,
    SCAR_HALF_LIFE_HOURS,
    apply_history_biases,
    decayed_strength,
    disclosure_payload,
    next_domain_biased,
    plain_scar,
)


@pytest.fixture
def mem_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "memory.json"
    monkeypatch.setenv("CURIOSITY_MEMORY_PATH", str(path))
    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    return path


def _mature_scar(
    target: str = "biology",
    *,
    strength: float = 1.0,
    hits: int = MIN_HITS_FOR_SCAR,
    updated_at: str = "2026-07-30T00:00:00+00:00",
) -> dict:
    return {
        "target": target,
        "kind": "domain",
        "strength": strength,
        "hits": hits,
        "updated_at": updated_at,
    }


def test_two_instances_with_different_histories_diverge(mem_path: Path) -> None:
    """Same command, different scars/affinities → different trajectories."""
    path_a = mem_path.parent / "mem_a.json"
    path_b = mem_path.parent / "mem_b.json"

    mem_a = PersistentMemory.load(path_a)
    # Scar the default jump target from ai → biology so A skips to materials.
    mem_a.scars = [_mature_scar("biology", strength=1.0)]
    mem_a.save()

    mem_b = PersistentMemory.load(path_b)
    # Affinity on biology keeps (or pulls toward) the default jump.
    mem_b.affinities = [
        {
            "target": "biology",
            "kind": "domain",
            "strength": 1.0,
            "hits": MIN_HITS_FOR_SCAR,
            "updated_at": "2026-07-30T00:00:00+00:00",
        }
    ]
    mem_b.save()

    run_a = explore(
        domain="ai",
        steps=4,
        n_return=5,
        seed=42,
        persist_memory=True,
        memory_path=str(path_a),
    )
    run_b = explore(
        domain="ai",
        steps=4,
        n_return=5,
        seed=42,
        persist_memory=True,
        memory_path=str(path_b),
    )

    domains_a = run_a["trajectory"]["domains_visited"]
    domains_b = run_b["trajectory"]["domains_visited"]
    assert domains_a != domains_b or json.dumps(run_a["trajectory"], sort_keys=True) != json.dumps(
        run_b["trajectory"], sort_keys=True
    ), (domains_a, domains_b)

    # Scar instance should avoid biology when it jumps.
    if len(domains_a) > 1:
        assert "biology" not in domains_a or "materials" in domains_a


def test_a_scar_decays_and_eventually_stops_mattering() -> None:
    stamped = "2026-07-30T00:00:00+00:00"
    now = datetime(2026, 7, 30, 0, 0, tzinfo=UTC)
    scar = _mature_scar("ai", strength=1.0, updated_at=stamped)

    fresh_s, fresh_f = decayed_strength(1.0, stamped, now=now)
    assert fresh_f == pytest.approx(1.0)
    assert fresh_s == pytest.approx(1.0)

    cfg = CuriosityConfig(
        domain="ai",
        n_candidates=16,
        value_profile=resolve_value_profile(),
        seed=42,
    )
    cfg_fresh, apps_fresh = apply_history_biases(cfg, [scar], [], now=now)
    assert apps_fresh
    assert abs(apps_fresh[0].magnitude) >= MIN_ACTIVE_STRENGTH
    assert cfg_fresh.n_candidates < cfg.n_candidates or (
        cfg_fresh.value_profile.min_answerability > cfg.value_profile.min_answerability
    )

    # Many half-lives later → residual below the active floor.
    later = now + timedelta(hours=SCAR_HALF_LIFE_HOURS * 10)
    faded_s, faded_f = decayed_strength(1.0, stamped, now=later)
    assert faded_f < 0.01
    assert faded_s < MIN_ACTIVE_STRENGTH

    cfg_faded, apps_faded = apply_history_biases(cfg, [scar], [], now=later)
    assert apps_faded == []
    assert cfg_faded.n_candidates == cfg.n_candidates
    assert cfg_faded.value_profile.min_answerability == cfg.value_profile.min_answerability

    # Domain jump also stops caring.
    nxt, bias = next_domain_biased(
        "ai",
        ["ai"],
        scars=[_mature_scar("biology", strength=1.0, updated_at=stamped)],
        now=later,
    )
    assert nxt == "biology"  # default jump restored
    assert bias is None


def test_scar_influence_is_bounded_and_always_disclosed(mem_path: Path) -> None:
    assert MAX_SCAR_BIAS == MAX_WEIGHT_DELTA
    assert MAX_AFFINITY_BIAS <= MAX_SCAR_BIAS

    stamped = "2026-07-30T12:00:00+00:00"
    # Absurd raw strength — magnitude must still cap.
    scar = _mature_scar("ai", strength=99.0, hits=9, updated_at=stamped)
    cfg = CuriosityConfig(
        domain="ai",
        n_candidates=16,
        value_profile=resolve_value_profile(),
        seed=42,
    )
    now = datetime(2026, 7, 30, 12, 0, tzinfo=UTC)
    new_cfg, apps = apply_history_biases(cfg, [scar], [], now=now)
    assert apps
    for app in apps:
        assert abs(app.magnitude) <= MAX_SCAR_BIAS + 1e-9
        assert abs(app.magnitude) <= MAX_WEIGHT_DELTA + 1e-9

    disclosed = disclosure_payload(apps)
    assert disclosed is not None
    assert disclosed["max_bias"] == MAX_SCAR_BIAS
    assert disclosed["peak_magnitude"] <= MAX_SCAR_BIAS + 1e-9
    assert all("magnitude" in b and "plain" in b for b in disclosed["biases"])

    mem = PersistentMemory.load(mem_path)
    mem.scars = [scar]
    mem.save()

    result = explore(
        domain="ai",
        steps=2,
        n_return=3,
        seed=42,
        persist_memory=True,
        memory_path=str(mem_path),
    )
    assert "scar_affinities" in result
    payload = result["scar_affinities"]
    assert payload["biases"]
    for bias in payload["biases"]:
        assert abs(float(bias["magnitude"])) <= MAX_SCAR_BIAS + 1e-9
        assert bias["bounded_by"]
        assert bias["plain"]

    # Plain language on memory show.
    shown = PersistentMemory.load(mem_path).show()
    assert shown["scars_plain"]
    assert (
        "raising the bar" in shown["scars_plain"][0].lower()
        or "went nowhere" in shown["scars_plain"][0].lower()
    )
    assert (
        "raising the bar" in plain_scar(scar).lower() or "went nowhere" in plain_scar(scar).lower()
    )


def test_a_fresh_install_behaves_identically_to_today(
    mem_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty / opted-out memory must not change the explore payload."""
    monkeypatch.setenv("CURIOSITY_NO_MEMORY", "1")
    assert memory_disabled()

    baseline = explore(domain="ai", steps=2, n_return=3, seed=42)
    with_flag = explore(
        domain="ai",
        steps=2,
        n_return=3,
        seed=42,
        persist_memory=True,
        memory_path=str(mem_path),
    )
    assert json.dumps(baseline, sort_keys=True) == json.dumps(with_flag, sort_keys=True)
    assert "scar_affinities" not in baseline
    assert not mem_path.exists()

    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)

    default_a = explore(domain="ai", steps=2, n_return=3, seed=42)
    default_b = explore(domain="ai", steps=2, n_return=3, seed=42, persist_memory=False)
    assert json.dumps(default_a, sort_keys=True) == json.dumps(default_b, sort_keys=True)
    assert "scar_affinities" not in default_a

    # First persist with empty history: no scar bias key (immature / empty).
    persisted = explore(
        domain="ai",
        steps=2,
        n_return=3,
        seed=42,
        persist_memory=True,
        memory_path=str(mem_path),
    )
    assert "scar_affinities" not in persisted
    assert json.dumps(default_a, sort_keys=True) == json.dumps(persisted, sort_keys=True)
