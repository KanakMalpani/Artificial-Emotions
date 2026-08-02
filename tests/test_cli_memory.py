"""CLI memory surface — show / avoiding / forget / reset via main([...]).

Covers cli_pkg/commands/memory.py only. Temp paths; never ~/.artificial_emotions/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from artificial_emotions.avoidance import MIN_ENCOUNTERS_FOR_AVOIDANCE
from artificial_emotions.cli import main
from artificial_emotions.memory import PersistentMemory


@pytest.fixture
def mem_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "memory.json"
    monkeypatch.setenv("CURIOSITY_MEMORY_PATH", str(path))
    monkeypatch.delenv("CURIOSITY_NO_MEMORY", raising=False)
    return path


def _seed_session(path: Path, *, session_id: str = "sess_a", qid: str = "q_a") -> None:
    mem = PersistentMemory.load(path)
    mem.record_session(
        domain="ai",
        topic="cli-memory",
        steps_taken=1,
        primary_feeling="curiosity",
        question_ids=[qid],
        best_question_id=qid,
        session_id=session_id,
    )
    mem.save()


def test_memory_show_prints_privacy_notice(
    mem_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_session(mem_path)
    assert main(["memory", "show", "--path", str(mem_path)]) == 0
    out = capsys.readouterr().out
    assert "memory file:" in out
    assert "CURIOSITY_NO_MEMORY" in out
    assert "emotions memory" in out or "forget" in out


def test_memory_show_json_includes_privacy_notice(
    mem_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_session(mem_path)
    assert main(["memory", "show", "--path", str(mem_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert "privacy_notice" in payload
    assert "CURIOSITY_NO_MEMORY" in payload["privacy_notice"]
    assert len(payload["sessions"]) == 1


def test_memory_avoiding_empty_text_and_json(
    mem_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["memory", "avoiding", "--path", str(mem_path)]) == 0
    text = capsys.readouterr().out
    assert "No persistent non-selection" in text
    assert "cannot distinguish" in text.lower()

    assert main(["memory", "avoiding", "--path", str(mem_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["avoiding"] == []
    assert payload["count"] == 0
    assert payload["min_encounters"] == MIN_ENCOUNTERS_FOR_AVOIDANCE


def test_memory_avoiding_lists_patterns(mem_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    mem = PersistentMemory.load(mem_path)
    for i in range(MIN_ENCOUNTERS_FOR_AVOIDANCE):
        mem.record_session(
            domain="ai",
            session_id=f"s{i}",
            question_ids=["ai-04", "other"],
            best_question_id="other",
        )
    mem.save()

    assert main(["memory", "avoiding", "--path", str(mem_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["avoiding"][0]["question_id"] == "ai-04"
    assert payload["avoiding"][0]["selections"] == 0

    assert main(["memory", "avoiding", "--path", str(mem_path)]) == 0
    text = capsys.readouterr().out
    assert "ai-04" in text
    assert "avoiding:" in text


def test_memory_forget_confirms_via_args(
    mem_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_session(mem_path, session_id="sess_drop", qid="q_keep")
    assert main(["memory", "forget", "sess_drop", "--path", str(mem_path), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["forgot"] is True
    assert result["kind"] == "session"

    assert main(["memory", "show", "--path", str(mem_path), "--json"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert all(s["session_id"] != "sess_drop" for s in shown["sessions"])
    assert shown["encounters"].get("q_keep") == 1

    assert main(["memory", "forget", "sessions", "--path", str(mem_path)]) == 0
    assert "forgot:" in capsys.readouterr().out


def test_memory_forget_miss_exits_one(mem_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["memory", "forget", "no-such-thing", "--path", str(mem_path)]) == 1
    err = capsys.readouterr().err
    assert "nothing forgotten" in err


def test_memory_reset_wipes_file(mem_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _seed_session(mem_path)
    assert mem_path.is_file()

    assert main(["memory", "reset", "--path", str(mem_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["reset"] is True
    assert payload["deleted_file"] is True
    assert not mem_path.exists()

    # Second reset: still ok when file already gone.
    assert main(["memory", "reset", "--path", str(mem_path)]) == 0
    assert "memory reset" in capsys.readouterr().out


def test_memory_usage_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["memory"]) == 2
    err = capsys.readouterr().err
    assert "Usage:" in err
    assert "show" in err and "forget" in err and "reset" in err and "avoiding" in err


def test_curiosity_no_memory_short_circuits(
    mem_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_session(mem_path)
    monkeypatch.setenv("CURIOSITY_NO_MEMORY", "1")

    assert main(["memory", "show", "--path", str(mem_path)]) == 0
    captured = capsys.readouterr()
    assert "Persistent memory disabled" in captured.err
    assert captured.out == ""

    assert main(["memory", "show", "--path", str(mem_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["disabled"] is True
    assert "CURIOSITY_NO_MEMORY" in payload["reason"]

    # Opt-out must not mutate the file via CLI.
    before = mem_path.read_text(encoding="utf-8")
    assert main(["memory", "reset", "--path", str(mem_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["disabled"] is True
    assert mem_path.read_text(encoding="utf-8") == before


def test_emotions_nested_memory_dispatch(
    mem_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_session(mem_path)
    assert main(["emotions", "memory", "show", "--path", str(mem_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["privacy_notice"]
    assert len(payload["sessions"]) == 1

    assert main(["emotions", "memory"]) == 2
    assert "Usage:" in capsys.readouterr().err
