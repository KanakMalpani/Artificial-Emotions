"""A2 mood carryover — persist, decay, bias thresholds, never fabricate evidence."""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from artificial_emotions.affect import (
    DEFAULT_MIN_SIGNAL,
    MOOD_HALF_LIFE_HOURS,
    MoodThresholdBias,
    decay_factor,
    decay_mood_pad,
    threshold_bias_from_pad,
)
from artificial_emotions.appraisal import RULES, appraise_run
from artificial_emotions.memory import MoodState, PersistentMemory
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine


@pytest.fixture
def mem_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "memory.json"
    monkeypatch.setenv("CURIOSITY_MEMORY_PATH", str(path))
    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    return path


@pytest.fixture(scope="module")
def ranked():
    return CuriosityEngine(
        CuriosityConfig(domain="ai", use_llm=False, use_literature=False, n_return=5)
    ).run()


def test_mood_persists_across_processes(mem_path: Path) -> None:
    write = f"""
from artificial_emotions.memory import MoodState, PersistentMemory
m = PersistentMemory.load(r"{mem_path}")
m.mood_carryover = MoodState(
    pleasure=-0.55,
    arousal=0.72,
    dominance=-0.2,
    updated_at="2026-07-30T12:00:00+00:00",
)
assert m.save()
print("wrote")
"""
    read = f"""
from artificial_emotions.memory import PersistentMemory
m = PersistentMemory.load(r"{mem_path}")
mood = m.mood_carryover
assert abs(mood.pleasure - (-0.55)) < 1e-9, mood
assert abs(mood.arousal - 0.72) < 1e-9, mood
assert abs(mood.dominance - (-0.2)) < 1e-9, mood
assert mood.updated_at == "2026-07-30T12:00:00+00:00"
print("ok")
"""
    env = {**os.environ, "CURIOSITY_MEMORY_PATH": str(mem_path)}
    env.pop("CURIOSITY_NO_MEMORY", None)
    w = subprocess.run(
        [sys.executable, "-c", write], capture_output=True, text=True, env=env, check=False
    )
    assert w.returncode == 0, w.stderr
    r = subprocess.run(
        [sys.executable, "-c", read], capture_output=True, text=True, env=env, check=False
    )
    assert r.returncode == 0, r.stderr
    assert "ok" in r.stdout


def test_mood_decays_toward_neutral_with_elapsed_time() -> None:
    stamped = "2026-07-30T00:00:00+00:00"
    now = datetime(2026, 7, 30, 0, 0, tzinfo=UTC)

    # Fresh: full residual.
    p0, a0, d0, f0 = decay_mood_pad(-0.8, 0.6, 0.4, stamped, now=now)
    assert f0 == pytest.approx(1.0)
    assert p0 == pytest.approx(-0.8)

    # One half-life later → half residual.
    later = now + timedelta(hours=MOOD_HALF_LIFE_HOURS)
    p1, a1, d1, f1 = decay_mood_pad(-0.8, 0.6, 0.4, stamped, now=later)
    assert f1 == pytest.approx(0.5)
    assert p1 == pytest.approx(-0.4)
    assert a1 == pytest.approx(0.3)
    assert d1 == pytest.approx(0.2)

    # A week later → essentially gone.
    week = now + timedelta(days=7)
    p2, a2, d2, f2 = decay_mood_pad(-0.8, 0.6, 0.4, stamped, now=week)
    assert f2 < 0.01
    assert abs(p2) < 0.01
    assert abs(a2) < 0.01

    # MoodState.decayed mirrors the same curve.
    stored = MoodState(pleasure=-0.8, arousal=0.6, dominance=0.4, updated_at=stamped)
    decayed = stored.decayed(at=later)
    assert decayed.pleasure == pytest.approx(-0.4)
    assert decay_factor(stamped, now=later) == pytest.approx(0.5)


def test_carryover_biases_thresholds_but_never_fabricates_evidence(ranked) -> None:
    """Carryover shifts floors for supported signals; invents nothing without evidence."""
    # Strong negative residual mood (frustrated / anxious PAD).
    bias = MoodThresholdBias(
        pleasure=-0.85,
        arousal=0.75,
        dominance=-0.25,
        decay_factor=1.0,
    )
    assert bias.is_active

    # Congruent negative emotion (frustration P≈-0.45) → lower floor.
    # Incongruent positive emotion (hope P≈+0.45) → higher floor.
    frust_floor = bias.floor_for(-0.45)
    hope_floor = bias.floor_for(0.45)
    assert frust_floor < DEFAULT_MIN_SIGNAL < hope_floor

    # Near-threshold weight: clears congruent floor, fails the default floor.
    near = (frust_floor + DEFAULT_MIN_SIGNAL) / 2.0
    assert frust_floor <= near < DEFAULT_MIN_SIGNAL
    assert near < hope_floor  # incongruent gate stays closed

    # Fabrication guard: frustration requires steps_without_progress >= 2.
    # With zero dead-end steps the rule returns None — mood must not invent it.
    why, rule = RULES["frustration"]
    from artificial_emotions.appraisal import build_context

    ctx = build_context(ranked, steps_without_progress=0)
    assert rule(ctx) is None

    signals = appraise_run(
        ranked,
        steps_without_progress=0,
        mood_bias=bias,
    )
    assert "frustration" not in {s.emotion for s in signals}

    # With real support, frustration still fires (mood does not erase evidence).
    with_support = appraise_run(
        ranked,
        steps_without_progress=3,
        mood_bias=bias,
    )
    assert "frustration" in {s.emotion for s in with_support}

    # threshold_bias_from_pad applies decay before floors.
    stamped = "2026-07-30T00:00:00+00:00"
    week_later = datetime(2026, 8, 6, 0, 0, tzinfo=UTC)
    faded = threshold_bias_from_pad(
        -0.85,
        0.75,
        -0.25,
        updated_at=stamped,
        now=week_later,
    )
    assert not faded.is_active or abs(faded.pleasure) < 0.01
    assert faded.floor_for(-0.45) == pytest.approx(DEFAULT_MIN_SIGNAL, abs=1e-4)


def test_session_end_writes_mood_with_timestamp(mem_path: Path) -> None:
    mem = PersistentMemory.load(mem_path)
    mem.record_explore_result(
        {
            "domain_started": "ai",
            "topic": "",
            "steps_taken": 1,
            "stopped_because": "test",
            "trajectory": {"steps": []},
            "final_feeling": {
                "mood": {"P": -0.4, "A": 0.55, "D": 0.1, "qualitative": {}},
            },
            "final_mix": {"primary": "frustration"},
            "best_found": None,
        }
    )
    mem.save()
    reloaded = PersistentMemory.load(mem_path)
    assert reloaded.mood_carryover.pleasure == pytest.approx(-0.4)
    assert reloaded.mood_carryover.arousal == pytest.approx(0.55)
    assert reloaded.mood_carryover.updated_at is not None
