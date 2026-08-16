"""Shared preference-event parse seam (JSONL + in-memory)."""

from __future__ import annotations

from pathlib import Path

import pytest

from artificial_emotions.eval_report import build_calibration_report
from artificial_emotions.outcome_loop import dry_run_outcome_loop
from artificial_emotions.preferences import (
    PreferenceEvent,
    coerce_preference_event,
    load_preference_events,
    normalize_preference_events,
    summarize_preferences,
)
from artificial_emotions.timeutil import parse_iso, utc_now_iso


def test_preference_event_ts_uses_utc_now_iso():
    assert PreferenceEvent.model_fields["ts"].default_factory is utc_now_iso
    ev = PreferenceEvent(event_type="note")
    assert parse_iso(ev.ts) is not None


def test_normalize_keeps_events_and_skips_junk():
    keep = PreferenceEvent(event_type="prefer", question_id="q-keep")
    rows = normalize_preference_events(
        [
            keep,
            {"event_type": "reject", "question_id": "q-dict"},
            {"not": "an event"},
            "nope",
            None,
        ]
    )
    assert [e.question_id for e in rows] == ["q-keep", "q-dict"]


def test_coerce_preference_event_returns_none_for_junk():
    assert coerce_preference_event({"not": "an event"}) is None
    ev = coerce_preference_event({"event_type": "outcome", "question_id": "q1"})
    assert ev is not None
    assert ev.event_type == "outcome"


def test_coerce_skips_json_decode_and_validation_errors(caplog):
    with caplog.at_level("WARNING", logger="artificial_emotions.preferences"):
        assert coerce_preference_event("nope") is None
        assert coerce_preference_event("{not json") is None
        assert coerce_preference_event({"event_type": ["prefer"]}) is None
    assert any("unreadable preference event" in rec.message for rec in caplog.records)


def test_coerce_accepts_json_string_events():
    raw = '{"event_type":"prefer","question_id":"from-json"}'
    ev = coerce_preference_event(raw)
    assert ev is not None
    assert ev.question_id == "from-json"


def test_coerce_propagates_unexpected_errors(monkeypatch: pytest.MonkeyPatch):
    def boom(*_a, **_k):
        raise RuntimeError("validator bug")

    monkeypatch.setattr(PreferenceEvent, "model_validate", boom)
    with pytest.raises(RuntimeError, match="validator bug"):
        coerce_preference_event({"event_type": "prefer", "question_id": "q"})


def test_normalize_propagates_unexpected_errors(monkeypatch: pytest.MonkeyPatch):
    def boom(*_a, **_k):
        raise AttributeError("unexpected parse bug")

    monkeypatch.setattr(PreferenceEvent, "model_validate", boom)
    with pytest.raises(AttributeError, match="unexpected parse bug"):
        normalize_preference_events([{"event_type": "prefer"}])


def test_corrupt_jsonl_line_is_skipped_and_logged(tmp_path: Path, caplog):
    path = tmp_path / "prefs.jsonl"
    path.write_text(
        '{"event_type":"prefer","question_id":"ok"}\n'
        "{not json\n"
        '{"event_type":"reject","question_id":"also-ok"}\n',
        encoding="utf-8",
    )
    with caplog.at_level("WARNING", logger="artificial_emotions.preferences"):
        rows = load_preference_events(path)
    assert [e.question_id for e in rows] == ["ok", "also-ok"]
    assert any("corrupt preference JSONL" in rec.message for rec in caplog.records)


def test_summarize_and_eval_report_share_the_seam():
    events = [
        PreferenceEvent(event_type="prefer", question_id="a", profile_name="humanity_default"),
        {"bogus": True},
    ]
    summary = summarize_preferences(events, profile_name="humanity_default")
    assert summary["n_events"] == 1
    report = build_calibration_report(events, profile_name="humanity_default")
    assert report["n_events"] == 1
    assert "not calibrated" in report["honesty"].lower()


def test_single_preference_event_is_not_iterated_as_fields():
    keep = PreferenceEvent(event_type="prefer", question_id="solo")
    rows = normalize_preference_events(keep)
    assert [e.question_id for e in rows] == ["solo"]


def test_learn_hints_uses_shared_seam_and_logs_junk(caplog):
    from artificial_emotions.preferences import learn_profile_weight_hints

    events = [
        PreferenceEvent(
            event_type="prefer",
            question_id="a",
            score_axes={"impact": 0.8, "neglectedness": 0.4},
        ),
        PreferenceEvent(
            event_type="reject",
            question_id="b",
            score_axes={"impact": 0.2, "neglectedness": 0.7},
        ),
        {"not": "an event"},
    ]
    with caplog.at_level("WARNING", logger="artificial_emotions.preferences"):
        hints = learn_profile_weight_hints(events, profile_name="humanity_default")
    assert hints["n_prefer"] == 1
    assert hints["n_reject"] == 1
    assert any("unreadable preference event" in rec.message for rec in caplog.records)


def test_preferences_reexports_event_seam():
    """CLI/HTTP/MCP/tests keep importing from preferences."""
    from artificial_emotions import preference_events, preferences

    assert preferences.PreferenceEvent is preference_events.PreferenceEvent
    assert preferences.SCHEMA_VERSION is preference_events.SCHEMA_VERSION
    assert preferences.append_preference_event is preference_events.append_preference_event
    assert preferences.coerce_preference_event is preference_events.coerce_preference_event
    assert preferences.events_from_ranked is preference_events.events_from_ranked
    assert preferences.load_preference_events is preference_events.load_preference_events
    assert preferences.normalize_preference_events is preference_events.normalize_preference_events
    assert preferences.outcome_for_appraisal is preference_events.outcome_for_appraisal
    assert preferences.read_preference_events is preference_events.read_preference_events


def test_outcome_loop_iterable_skips_unreadable_items():
    payload = dry_run_outcome_loop(
        [
            {
                "event_type": "outcome",
                "question_id": "loop-ok",
                "labels": {"result": "partial_progress"},
                "domain": "ai",
            },
            {"nope": True},
        ]
    )
    assert payload["ok"] is True
    assert payload["n_outcome"] == 1
    assert payload["experiments_run"] == 0
    assert payload["suggested_rerank"][0]["question_id"] == "loop-ok"
