"""Outcome JSONL dry-run loop — suggested re-rank / next explore, not experiments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from artificial_emotions import __version__
from artificial_emotions.cli import build_parser, main
from artificial_emotions.outcome_loop import (
    default_outcome_loop_fixture,
    dry_run_outcome_loop,
)
from artificial_emotions.preferences import PreferenceEvent, append_preference_event


def _keys(obj: object, acc: set[str] | None = None) -> set[str]:
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(str(k))
            _keys(v, acc)
    elif isinstance(obj, list):
        for item in obj:
            _keys(item, acc)
    return acc


def test_default_fixture_exists():
    path = default_outcome_loop_fixture()
    assert path.is_file()


def test_dry_run_fixture_reranks_and_suggests_continue():
    payload = dry_run_outcome_loop(default_outcome_loop_fixture())
    assert payload["mode"] == "dry_run"
    assert payload["report"] == "outcome_loop_dry_run"
    assert payload["package_version"] == __version__
    assert payload["ok"] is True
    assert payload["reason"] == "ok"
    assert payload["experiments_run"] == 0
    assert payload["executed"] is False
    assert payload["ran_explore"] is False
    assert payload["n_outcome"] == 6  # five with ids + one missing id
    assert payload["n_non_outcome_ignored"] >= 1
    assert payload["by_result"]["partial_progress"] == 2
    assert payload["by_result"]["null"] == 2
    assert payload["by_result"]["answered"] == 1
    assert payload["by_result"]["abandoned"] == 1

    by_id = {row["question_id"]: row for row in payload["suggested_rerank"]}
    assert "loop-ignore" not in by_id
    assert by_id["loop-a"]["reason"] == "partial_progress"
    assert by_id["loop-a"]["bucket"] == "continue"
    assert by_id["loop-a"]["delta"] > 0
    assert by_id["loop-a"]["suggested_rank"] == 1
    assert by_id["loop-b"]["bucket"] == "dead_end"
    assert by_id["loop-b"]["delta"] < 0
    assert by_id["loop-c"]["bucket"] == "resolved"
    assert by_id["loop-c"]["delta"] < 0

    nxt = payload["next_explore"]
    assert nxt["action"] == "continue"
    assert nxt["question_id"] == "loop-a"
    assert nxt["executed"] is False
    assert nxt["suggested_command"]
    honesty = payload["honesty"].lower()
    assert "dry-run" in honesty
    assert "not a lab closed-loop" in honesty
    assert "does not run experiments" in honesty
    assert "not evsi" in honesty
    keys = _keys(payload)
    assert not (keys & {"accuracy", "accuracy_pct", "ece", "brier"})


def test_profile_filter_drops_other_profile_outcomes():
    payload = dry_run_outcome_loop(
        default_outcome_loop_fixture(),
        profile_name="humanity_default",
    )
    ids = {row["question_id"] for row in payload["suggested_rerank"]}
    assert "loop-other" not in ids
    assert "loop-a" in ids
    assert payload["by_result"].get("abandoned", 0) == 0


def test_missing_file_is_fail_closed(tmp_path: Path):
    payload = dry_run_outcome_loop(tmp_path / "absent.jsonl")
    assert payload["ok"] is False
    assert payload["reason"] == "missing_outcomes_jsonl"
    assert payload["n_outcome"] == 0
    assert payload["next_explore"] is None
    assert payload["experiments_run"] == 0
    assert payload["executed"] is False


def test_empty_jsonl_is_silent(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    payload = dry_run_outcome_loop(path)
    assert payload["ok"] is True
    assert payload["reason"] == "no_outcomes"
    assert payload["suggested_rerank"] == []
    assert payload["next_explore"] is None


def test_prefer_only_jsonl_does_not_invent_a_next_step(tmp_path: Path):
    path = tmp_path / "prefer.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(event_type="prefer", question_id="only-pref"),
    )
    payload = dry_run_outcome_loop(path)
    assert payload["n_outcome"] == 0
    assert payload["n_non_outcome_ignored"] == 1
    assert payload["next_explore"] is None
    assert payload["suggested_rerank"] == []


def test_all_resolved_suggests_shift(tmp_path: Path):
    path = tmp_path / "done.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="outcome",
            question_id="done-1",
            labels={"result": "answered"},
        ),
    )
    payload = dry_run_outcome_loop(path)
    assert payload["next_explore"]["action"] == "shift"
    assert payload["next_explore"]["executed"] is False
    assert payload["suggested_rerank"][0]["delta"] < 0


def test_unrecognized_result_suggests_inspect(tmp_path: Path):
    path = tmp_path / "weird.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="outcome",
            question_id="weird-1",
            labels={"result": "maybe_later"},
        ),
    )
    payload = dry_run_outcome_loop(path)
    assert payload["next_explore"]["action"] == "inspect"
    assert payload["suggested_rerank"][0]["delta"] == 0.0
    assert payload["suggested_rerank"][0]["bucket"] == "unknown"


def test_inline_events_need_no_path():
    payload = dry_run_outcome_loop(
        [
            {
                "event_type": "outcome",
                "question_id": "inline-a",
                "domain": "physics",
                "labels": {"result": "partial_progress"},
            }
        ]
    )
    assert payload["outcomes_path"] is None
    assert payload["next_explore"]["question_id"] == "inline-a"
    assert payload["next_explore"]["suggested_command"] == (
        "emotions explore --domain physics --steps 1"
    )


def test_dry_run_never_calls_explore(monkeypatch):
    def boom(*_a, **_k):  # noqa: ARG001
        raise AssertionError("explore must not run during outcome-loop dry-run")

    monkeypatch.setattr("artificial_emotions.explore.explore", boom)
    dry_run_outcome_loop(default_outcome_loop_fixture())


def test_cli_json_fixture(capsys):
    path = default_outcome_loop_fixture()
    assert main(["loop", "--outcomes", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "dry_run"
    assert payload["next_explore"]["action"] == "continue"
    assert payload["experiments_run"] == 0
    blob = json.dumps(payload).lower()
    assert "lab closed-loop" in blob
    assert "does not run experiments" in blob


def test_cli_profile_filter(capsys):
    path = default_outcome_loop_fixture()
    assert (
        main(
            [
                "loop",
                "--outcomes",
                str(path),
                "--profile",
                "humanity_default",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    ids = {row["question_id"] for row in payload["suggested_rerank"]}
    assert "loop-other" not in ids


def test_cli_human_text(capsys):
    path = default_outcome_loop_fixture()
    assert main(["loop", "--outcomes", str(path)]) == 0
    out = capsys.readouterr().out.lower()
    assert "dry-run" in out
    assert "not experiment execution" in out
    assert "not a lab closed-loop" in out
    assert "loop-a" in out


def test_cli_missing_file_exits_one(capsys, tmp_path: Path):
    missing = tmp_path / "nope.jsonl"
    assert main(["loop", "--outcomes", str(missing), "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["reason"] == "missing_outcomes_jsonl"


def test_cli_requires_outcomes_flag():
    with pytest.raises(SystemExit) as exc:
        main(["loop"])
    assert exc.value.code != 0


def test_loop_is_wired_into_parser():
    parser = build_parser()
    sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    assert "loop" in sub.choices
    raw = sub.choices["loop"].format_help().lower().replace("-\n", "-")
    help_text = " ".join(raw.split())
    assert "--outcomes" in help_text
    assert "dry-run" in help_text
    assert "not a lab closed-loop" in help_text


def test_limits_names_dry_run_not_lab_closed_loop():
    text = (Path(__file__).resolve().parents[1] / "docs" / "LIMITS.md").read_text(encoding="utf-8")
    assert "emotions loop --outcomes" in text
    collapsed = " ".join(text.lower().replace("*", "").split())
    assert "not a lab closed-loop" in collapsed
    assert "not experiment execution" in collapsed or "does not run experiments" in collapsed
