"""Offline preference-JSONL calibration telemetry (W-cal) — not an accuracy report."""

from __future__ import annotations

import json
from pathlib import Path

from artificial_emotions.eval_report import (
    build_calibration_report,
    build_eval_report,
    default_calibration_fixture,
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


_FORBIDDEN_METRIC_KEYS = frozenset(
    {
        "accuracy",
        "accuracy_pct",
        "accuracy_percent",
        "match_rate",
        "status_accuracy",
        "ece",
        "brier",
    }
)


def _assert_no_accuracy_metrics(payload: dict) -> None:
    keys = _keys(payload)
    overlap = keys & _FORBIDDEN_METRIC_KEYS
    assert not overlap, f"calibration telemetry must not report {sorted(overlap)}"
    honesty = str(payload.get("honesty") or "").lower()
    assert "not calibrated" in honesty


def test_default_smoke_fixture_exists():
    path = default_calibration_fixture()
    assert path.is_file()


def test_calibration_report_counts_outcomes_and_hint_magnitudes():
    payload = build_calibration_report()
    _assert_no_accuracy_metrics(payload)
    assert payload["report"] == "preference_calibration_telemetry"
    assert payload["ok"] is True
    assert payload["reason"] == "ok"
    assert payload["n_events"] == 5
    assert payload["counts_by_type"]["prefer"] == 1
    assert payload["counts_by_type"]["reject"] == 1
    assert payload["counts_by_type"]["keep"] == 1
    assert payload["counts_by_type"]["outcome"] == 2
    outcomes = payload["outcomes"]
    assert outcomes["n_outcome"] == 2
    assert outcomes["by_result"]["partial_progress"] == 1
    assert outcomes["by_result"]["null"] == 1
    hm = payload["hint_magnitudes"]
    assert hm["ok"] is True
    assert hm["n_prefer"] >= 2  # prefer + keep; +outcome if hints consume them
    assert hm["n_reject"] >= 1
    assert hm["deltas"]["weight_impact"] > 0
    assert hm["l1"] > 0
    assert hm["max_abs"] > 0
    assert hm["n_nonzero"] >= 1
    assert "suggested_profile" not in hm
    if "n_outcome" in hm:
        assert isinstance(hm["n_outcome"], int)
        assert hm["n_outcome"] >= 0
    assert payload["docs"] == "evals/METHODOLOGY.md"


def test_calibration_report_missing_file(tmp_path: Path):
    payload = build_calibration_report(tmp_path / "absent.jsonl")
    _assert_no_accuracy_metrics(payload)
    assert payload["ok"] is False
    assert payload["reason"] == "missing_preference_jsonl"
    assert payload["n_events"] == 0
    assert payload["outcomes"]["n_outcome"] == 0
    assert payload["hint_magnitudes"]["l1"] == 0.0


def test_calibration_report_empty_jsonl(tmp_path: Path):
    path = tmp_path / "empty.jsonl"
    path.write_text("", encoding="utf-8")
    payload = build_calibration_report(path)
    _assert_no_accuracy_metrics(payload)
    assert payload["ok"] is True
    assert payload["n_events"] == 0
    assert payload["hint_magnitudes"]["ok"] is False


def test_calibration_report_profile_filter(tmp_path: Path):
    path = tmp_path / "prefs.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="prefer",
            profile_name="humanity_default",
            question_id="a",
            score_axes={
                "impact": 0.9,
                "neglectedness": 0.8,
                "tractability": 0.3,
                "surprise": 0.7,
            },
        ),
    )
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="reject",
            profile_name="alignment_lab",
            question_id="b",
            score_axes={
                "impact": 0.2,
                "neglectedness": 0.2,
                "tractability": 0.9,
                "surprise": 0.2,
            },
        ),
    )
    payload = build_calibration_report(path, profile_name="humanity_default")
    assert payload["n_events"] == 1
    assert payload["counts_by_type"] == {"prefer": 1}


def test_calibration_report_outcome_events_without_hints():
    payload = build_calibration_report(
        [
            {
                "event_type": "outcome",
                "profile_name": "humanity_default",
                "question_id": "only-out",
                "labels": {"result": "partial_progress"},
            }
        ]
    )
    _assert_no_accuracy_metrics(payload)
    assert payload["outcomes"]["n_outcome"] == 1
    assert payload["outcomes"]["by_result"]["partial_progress"] == 1
    assert payload["hint_magnitudes"]["ok"] is False
    assert payload["hint_magnitudes"]["l1"] == 0.0


def test_calibration_forwards_outcome_hint_counts_if_present(monkeypatch):
    def fake_hints(events, *, profile_name=None):  # noqa: ARG001
        return {
            "ok": True,
            "reason": "ok",
            "n_prefer": 2,
            "n_reject": 1,
            "deltas": {"weight_impact": 0.04},
            "clamped_weights": [],
            "n_outcome": 2,
            "n_outcome_with_axes": 1,
        }

    monkeypatch.setattr(
        "artificial_emotions.preferences.learn_profile_weight_hints",
        fake_hints,
    )
    payload = build_calibration_report(
        [
            {
                "event_type": "prefer",
                "profile_name": "humanity_default",
                "question_id": "a",
                "score_axes": {
                    "impact": 0.9,
                    "neglectedness": 0.8,
                    "tractability": 0.3,
                    "surprise": 0.6,
                },
            }
        ]
    )
    hm = payload["hint_magnitudes"]
    assert hm["n_outcome"] == 2
    assert hm["n_outcome_with_axes"] == 1
    _assert_no_accuracy_metrics(payload)


def test_composite_report_unchanged_without_preference_path():
    report = build_eval_report()
    assert "calibration" not in report["sections"]
    assert "calibration" not in report["sections"]["diagnostics_first"]["order"]


def test_composite_report_optional_calibration_section():
    report = build_eval_report(preference_path=default_calibration_fixture())
    cal = report["sections"]["calibration"]
    assert cal["report"] == "preference_calibration_telemetry"
    assert "calibration" in report["sections"]["diagnostics_first"]["order"]
    _assert_no_accuracy_metrics(cal)


def test_eval_calibration_cli_json(capsys, tmp_path: Path):
    from artificial_emotions.cli import main

    path = tmp_path / "prefs.jsonl"
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="prefer",
            profile_name="humanity_default",
            question_id="a",
            score_axes={
                "impact": 0.9,
                "neglectedness": 0.85,
                "tractability": 0.3,
                "surprise": 0.7,
            },
        ),
    )
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="reject",
            profile_name="humanity_default",
            question_id="b",
            score_axes={
                "impact": 0.3,
                "neglectedness": 0.25,
                "tractability": 0.9,
                "surprise": 0.2,
            },
        ),
    )
    append_preference_event(
        path,
        PreferenceEvent(
            event_type="outcome",
            profile_name="humanity_default",
            question_id="a",
            labels={"result": "partial_progress"},
        ),
    )
    assert main(["eval", "calibration", "--path", str(path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    _assert_no_accuracy_metrics(payload)
    assert payload["counts_by_type"]["prefer"] == 1
    assert payload["outcomes"]["n_outcome"] == 1
    assert payload["hint_magnitudes"]["l1"] > 0


def test_eval_calibration_cli_default_fixture(capsys):
    from artificial_emotions.cli import main

    assert main(["eval", "calibration", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    _assert_no_accuracy_metrics(payload)
    assert payload["n_events"] >= 1


def test_eval_calibration_cli_human_text(capsys):
    from artificial_emotions.cli import main

    assert main(["eval", "calibration"]) == 0
    out = capsys.readouterr().out.lower()
    assert "not calibrated" in out
    assert "accuracy %" not in out


def test_methodology_documents_calibration_telemetry():
    root = Path(__file__).resolve().parents[1]
    text = (root / "evals" / "METHODOLOGY.md").read_text(encoding="utf-8")
    collapsed = " ".join(text.lower().split())
    assert "eval calibration" in collapsed
    assert "not a calibration certificate" in collapsed
    assert "hint magnitudes" in collapsed
    assert "not calibrated" in collapsed
    assert "does not publish an accuracy" in collapsed.replace("*", "")
