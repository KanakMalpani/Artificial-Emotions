"""A1 PersistentMemory — continuity across processes, inspectable, forgettable.

Library explore defaults off; CURIOSITY_NO_MEMORY=1 keeps today's offline payload.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from artificial_emotions.explore import explore
from artificial_emotions.memory import (
    MAX_SESSIONS,
    PersistentMemory,
    SessionRecord,
    memory_disabled,
)


@pytest.fixture
def mem_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "memory.json"
    monkeypatch.setenv("CURIOSITY_MEMORY_PATH", str(path))
    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    return path


def test_a_second_process_remembers_the_first(mem_path: Path) -> None:
    write = f"""
from artificial_emotions.memory import PersistentMemory
m = PersistentMemory.load(r"{mem_path}")
m.record_session(
    domain="ai",
    topic="continuity",
    steps_taken=2,
    primary_feeling="curiosity",
    question_ids=["q_from_process_one"],
    best_question_id="q_from_process_one",
)
assert m.save()
print("wrote")
"""
    read = f"""
from artificial_emotions.memory import PersistentMemory
m = PersistentMemory.load(r"{mem_path}")
assert any("q_from_process_one" in s.question_ids for s in m.sessions), m.sessions
assert m.encounters.get("q_from_process_one", 0) >= 1
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


def test_memory_file_is_human_readable_and_hand_editable(mem_path: Path) -> None:
    mem = PersistentMemory.load(mem_path)
    mem.record_session(domain="biology", topic="hand-edit", question_ids=["q_edit_me"])
    mem.save()

    text = mem_path.read_text(encoding="utf-8")
    assert "\n" in text
    assert '"schema_version"' in text
    assert '"sessions"' in text
    data = json.loads(text)
    assert isinstance(data, dict)
    assert data["sessions"][0]["domain"] == "biology"

    # Hand-edit: rename domain, add a note field the loader ignores safely.
    data["sessions"][0]["domain"] = "climate"
    data["sessions"][0]["topic"] = "edited by hand"
    mem_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    reloaded = PersistentMemory.load(mem_path)
    assert reloaded.sessions[0].domain == "climate"
    assert reloaded.sessions[0].topic == "edited by hand"
    assert reloaded.encounters.get("q_edit_me") == 1


def test_forget_actually_forgets(mem_path: Path) -> None:
    mem = PersistentMemory.load(mem_path)
    rec = mem.record_session(
        domain="ai",
        question_ids=["q_forgettable"],
        session_id="sess_forget_me",
    )
    mem.save()
    assert PersistentMemory.load(mem_path).encounters["q_forgettable"] == 1

    mem2 = PersistentMemory.load(mem_path)
    result = mem2.forget("sess_forget_me")
    assert result["forgot"] is True
    mem2.save()

    after = PersistentMemory.load(mem_path)
    assert all(s.session_id != "sess_forget_me" for s in after.sessions)
    # encounter count remains until forgotten explicitly
    assert after.encounters.get("q_forgettable") == 1

    mem3 = PersistentMemory.load(mem_path)
    assert mem3.forget("q_forgettable")["forgot"] is True
    mem3.save()
    gone = PersistentMemory.load(mem_path)
    assert "q_forgettable" not in gone.encounters
    assert rec.session_id not in {s.session_id for s in gone.sessions}


def test_memory_is_capped_and_evicts_oldest(mem_path: Path) -> None:
    mem = PersistentMemory.load(mem_path)
    for i in range(MAX_SESSIONS + 25):
        mem.record_session(
            domain="ai",
            session_id=f"s{i:04d}",
            question_ids=[f"q{i}"],
        )
    assert len(mem.sessions) == MAX_SESSIONS
    assert mem.sessions[0].session_id == f"s{25:04d}"
    assert mem.sessions[-1].session_id == f"s{MAX_SESSIONS + 24:04d}"
    mem.save()

    reloaded = PersistentMemory.load(mem_path)
    assert len(reloaded.sessions) == MAX_SESSIONS
    assert reloaded.sessions[0].session_id == f"s{25:04d}"
    assert "s0000" not in {s.session_id for s in reloaded.sessions}


def test_a_fresh_install_behaves_identically_to_today(
    mem_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Memory-less / opted-out runs match the default library path."""
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
    assert not mem_path.exists()

    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    assert not memory_disabled()

    default_a = explore(domain="ai", steps=2, n_return=3, seed=42)
    default_b = explore(domain="ai", steps=2, n_return=3, seed=42, persist_memory=False)
    assert json.dumps(default_a, sort_keys=True) == json.dumps(default_b, sort_keys=True)
    assert not mem_path.exists()

    # Persisting must not change the explore payload (write-only in A1).
    persisted = explore(
        domain="ai",
        steps=2,
        n_return=3,
        seed=42,
        persist_memory=True,
        memory_path=str(mem_path),
    )
    assert json.dumps(default_a, sort_keys=True) == json.dumps(persisted, sort_keys=True)
    assert mem_path.is_file()
    assert PersistentMemory.load(mem_path).sessions


def test_session_record_round_trip() -> None:
    raw = SessionRecord(
        session_id="abc",
        started_at="2026-07-30T00:00:00+00:00",
        domain="ai",
        question_ids=["q1"],
    ).to_dict()
    assert SessionRecord.from_dict(raw).session_id == "abc"
