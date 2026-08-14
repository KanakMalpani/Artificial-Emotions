"""VOI worksheet honesty: evsi is null, honesty=not_evsi. No invented numbers."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from artificial_emotions.agent_tools import dispatch_tool, mcp_tool_list
from artificial_emotions.api import app
from artificial_emotions.mcp_lint import lint_tool_description, lint_tool_specs
from artificial_emotions.voi import HONESTY_NOT_EVSI, estimate_evsi, fill_voi_worksheet


def test_estimate_evsi_none_without_data() -> None:
    assert estimate_evsi() is None
    assert estimate_evsi(psa_draws=[], utilities=[], options=[]) is None
    assert estimate_evsi(psa_draws="not-a-draw-list", utilities=[1.0], likelihood=1) is None


def test_estimate_evsi_ignores_score_axes() -> None:
    axes = [{"impact": 0.8, "surprise": 0.7, "neglectedness": 0.4}]
    assert estimate_evsi(psa_draws=axes, utilities=[0.1], likelihood=0.5, options=["a"]) is None


def test_estimate_evsi_none_even_with_dummy_psa() -> None:
    # No in-tree solver — do not invent a number.
    assert (
        estimate_evsi(
            psa_draws=[{"theta": 0.1}, {"theta": 0.9}],
            utilities=[1.0, 2.0],
            likelihood={"p": 0.5},
            options=["treat", "wait"],
        )
        is None
    )


def test_fill_voi_worksheet_honesty_keys() -> None:
    sheet = fill_voi_worksheet(
        question_id="q1",
        question="Which biomarkers predict healthspan under interventions?",
        operationalization="AUROC ≥ 0.7 across ≥2 intervention classes",
        profile_name="humanity_default",
        domain="biology",
    )
    assert sheet["evsi"] is None
    assert sheet["honesty"] == HONESTY_NOT_EVSI
    assert sheet["honesty"] == "not_evsi"
    assert "EVSI" in sheet["honesty_note"]
    encoded = json.dumps(sheet)
    parsed = json.loads(encoded)
    assert parsed["evsi"] is None
    assert "evsi" in parsed
    assert "honesty" in parsed
    assert "honesty_note" in parsed


def test_fill_overwrites_invented_template_evsi(tmp_path: Path) -> None:
    path = tmp_path / "tampered.json"
    path.write_text(
        json.dumps(
            {
                "honesty": "computed",
                "evsi": 12.3,
                "options": ["a", "b"],
                "link_to_ranked_question": {},
            }
        ),
        encoding="utf-8",
    )
    sheet = fill_voi_worksheet(template_path=path, question="Why X?")
    assert sheet["evsi"] is None
    assert sheet["honesty"] == "not_evsi"


def test_http_and_mcp_voi_honesty() -> None:
    client = TestClient(app)
    res = client.post(
        "/v1/voi/worksheet",
        json={"question": "Test unknown?", "profile_name": "humanity_default"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["evsi"] is None
    assert body["honesty"] == "not_evsi"

    out = dispatch_tool("voi_worksheet", {"question": "Why X?", "question_id": "q-mcp"})
    assert out["evsi"] is None
    assert out["honesty"] == "not_evsi"
    assert out["link_to_ranked_question"]["question_id"] == "q-mcp"


def test_voi_worksheet_tool_passes_mcp_lint() -> None:
    errors = lint_tool_specs(mcp_tool_list())
    assert errors == [], errors
    tool = next(t for t in mcp_tool_list() if t["name"] == "voi_worksheet")
    assert lint_tool_description("voi_worksheet", tool["description"]) == []
    blob = tool["description"].lower()
    assert "not evsi" in blob or "not_evsi" in blob
    assert "decision aid" in blob or "not oracle" in blob
