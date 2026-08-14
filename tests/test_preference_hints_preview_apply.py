"""CLI / MCP / HTTP preview vs apply for preference weight hints.

Default is preview. apply returns a profile copy — never overwrites a named
preset. HTTP/MCP take inline events only (no filesystem paths). Not calibrated.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from artificial_emotions.agent_tools import dispatch_tool, mcp_tool_list
from artificial_emotions.api import app
from artificial_emotions.api_pkg.schemas import PreferenceHintsRequest
from artificial_emotions.cli import main
from artificial_emotions.mcp_lint import lint_tool_specs
from artificial_emotions.models import CuriosityConfig, resolve_value_profile
from artificial_emotions.pipeline import CuriosityEngine
from artificial_emotions.preferences import (
    PreferenceEvent,
    append_preference_event,
    preview_or_apply_weight_hints,
)

_EVENTS = [
    {
        "event_type": "prefer",
        "profile_name": "humanity_default",
        "question_id": "a",
        "score_axes": {
            "impact": 0.85,
            "neglectedness": 0.7,
            "tractability": 0.35,
            "surprise": 0.65,
        },
    },
    {
        "event_type": "reject",
        "profile_name": "humanity_default",
        "question_id": "b",
        "score_axes": {
            "impact": 0.35,
            "neglectedness": 0.3,
            "tractability": 0.85,
            "surprise": 0.25,
        },
    },
]


def _write_jsonl(path: Path) -> Path:
    for raw in _EVENTS:
        append_preference_event(path, PreferenceEvent.model_validate(raw))
    return path


def test_preview_or_apply_defaults_to_preview_without_mutating_base():
    base = resolve_value_profile(profile_name="humanity_default")
    impact = base.weight_impact
    preview = preview_or_apply_weight_hints(_EVENTS, profile_name="humanity_default")
    assert preview["ok"] is True
    assert preview["mode"] == "preview"
    assert preview["applied"] is False
    assert "applied_profile" not in preview
    assert "suggested_profile" in preview
    assert base.weight_impact == impact
    assert "not calibrated" in (preview.get("honesty") or "").lower()

    applied = preview_or_apply_weight_hints(_EVENTS, profile_name="humanity_default", apply=True)
    assert applied["mode"] == "apply"
    assert applied["applied"] is True
    assert applied["applied_profile"]["weight_impact"] > impact
    assert base.weight_impact == impact
    assert applied["applied_profile"]["name"] != "humanity_default"


def test_cli_hints_preview_vs_apply(tmp_path: Path, capsys):
    path = _write_jsonl(tmp_path / "hints.jsonl")
    assert main(["preferences", "hints", "--path", str(path), "--json"]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["mode"] == "preview"
    assert preview["applied"] is False
    assert "applied_profile" not in preview

    assert main(["preferences", "hints", "--path", str(path), "--apply", "--json"]) == 0
    applied = json.loads(capsys.readouterr().out)
    assert applied["mode"] == "apply"
    assert applied["applied"] is True
    assert (
        applied["applied_profile"]["weight_impact"] == preview["suggested_profile"]["weight_impact"]
    )


def test_http_hints_apply_flag_and_no_path_field():
    assert "path" not in PreferenceHintsRequest.model_fields
    assert "events_path" not in PreferenceHintsRequest.model_fields
    assert "preference_learn_path" not in PreferenceHintsRequest.model_fields
    assert PreferenceHintsRequest.model_fields["apply"].default is False

    client = TestClient(app)
    preview = client.post(
        "/v1/preferences/hints",
        json={"profile_name": "humanity_default", "events": _EVENTS},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["mode"] == "preview"
    assert body["applied"] is False
    assert "applied_profile" not in body

    applied = client.post(
        "/v1/preferences/hints",
        json={
            "profile_name": "humanity_default",
            "events": _EVENTS,
            "apply": True,
        },
    )
    assert applied.status_code == 200
    applied_body = applied.json()
    assert applied_body["mode"] == "apply"
    assert applied_body["applied"] is True
    assert (
        applied_body["applied_profile"]["weight_impact"]
        == body["suggested_profile"]["weight_impact"]
    )


def test_http_hints_ignores_path_injection(tmp_path: Path):
    evil = tmp_path / "empty.jsonl"
    evil.write_text("", encoding="utf-8")
    client = TestClient(app)
    res = client.post(
        "/v1/preferences/hints",
        json={
            "path": str(evil),
            "events_path": str(evil),
            "preference_learn_path": str(evil),
            "profile_name": "humanity_default",
            "events": _EVENTS,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["mode"] == "preview"
    assert "weight_impact" in data["deltas"]


def test_mcp_preference_weight_hints_preview_apply_and_path_refuse():
    names = {t["name"] for t in mcp_tool_list()}
    assert "preference_weight_hints" in names
    tool = next(t for t in mcp_tool_list() if t["name"] == "preference_weight_hints")
    assert "path" not in tool["inputSchema"]["properties"]
    assert tool["inputSchema"]["properties"]["apply"]["default"] is False
    assert lint_tool_specs([tool]) == []

    preview = dispatch_tool("preference_weight_hints", {"events": _EVENTS})
    assert preview["mode"] == "preview"
    assert preview["applied"] is False
    assert "applied_profile" not in preview

    applied = dispatch_tool("preference_weight_hints", {"events": _EVENTS, "apply": True})
    assert applied["mode"] == "apply"
    assert applied["applied"] is True
    assert "applied_profile" in applied

    refused = dispatch_tool(
        "preference_weight_hints",
        {"path": "/tmp/hints.jsonl", "events": _EVENTS},
    )
    assert refused["ok"] is False
    assert refused["reason"] == "filesystem_paths_not_accepted"
    assert refused["applied"] is False


def test_run_preference_learn_preview_vs_apply(tmp_path: Path):
    path = _write_jsonl(tmp_path / "learn.jsonl")
    preview_profile = resolve_value_profile(profile_name="humanity_default")
    impact = preview_profile.weight_impact
    preview_engine = CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            use_literature=False,
            use_llm=False,
            n_return=2,
            value_profile=preview_profile,
            preference_learn_path=str(path),
            preference_learn_apply=False,
        )
    )
    preview_rows = preview_engine.run()
    assert preview_rows
    assert preview_engine.config.value_profile.weight_impact == impact
    assert preview_engine.config.value_profile.name == "humanity_default"
    meta = next(
        r.metadata["preference_weight_hints"]
        for r in preview_rows
        if (r.metadata or {}).get("preference_weight_hints")
    )
    assert meta["mode"] == "preview"
    assert meta["applied"] is False

    apply_profile = resolve_value_profile(profile_name="humanity_default")
    apply_engine = CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            use_literature=False,
            use_llm=False,
            n_return=2,
            value_profile=apply_profile,
            preference_learn_path=str(path),
            preference_learn_apply=True,
        )
    )
    apply_rows = apply_engine.run()
    assert apply_rows
    assert apply_engine.config.value_profile.weight_impact > impact
    apply_meta = next(
        r.metadata["preference_weight_hints"]
        for r in apply_rows
        if (r.metadata or {}).get("preference_weight_hints")
    )
    assert apply_meta["mode"] == "apply"
    assert apply_meta["applied"] is True


def test_agent_tools_http_fallback_for_hints():
    client = TestClient(app)
    tools = client.get("/v1/agent/tools").json()
    assert tools["http_fallbacks"]["preference_weight_hints"] == ("POST /v1/preferences/hints")
    agent = client.get("/v1/agent").json()
    assert "preference_weight_hints" in agent["mcp"]["tools"]
