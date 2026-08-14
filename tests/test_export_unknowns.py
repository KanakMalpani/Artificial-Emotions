"""Ranked-unknowns export: CLI file/JSON + HTTP body. No webhook URLs (SSRF)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from artificial_emotions.agent_tools import dispatch_tool, mcp_tool_list
from artificial_emotions.api import app
from artificial_emotions.api_pkg.schemas import ExportUnknownsRequest, RunRequest
from artificial_emotions.cli import build_parser, main
from artificial_emotions.export_unknowns import (
    FORMAT_ID,
    coerce_ranked_questions,
    export_unknowns,
    reject_webhook_fields,
    write_unknowns_export,
)
from artificial_emotions.mcp_lint import lint_tool_specs
from artificial_emotions.models import CuriosityConfig
from artificial_emotions.pipeline import CuriosityEngine


def _offline_engine(n: int = 2) -> CuriosityEngine:
    return CuriosityEngine(
        CuriosityConfig(
            domain="ai",
            n_return=n,
            n_candidates=8,
            use_llm=False,
            use_literature=False,
        )
    )


def _ranked_dicts(n: int = 2) -> list[dict]:
    return _offline_engine(n).run_dict()


def test_export_unknowns_reuses_pipeline_output_without_rerank():
    rows = _ranked_dicts(2)
    doc = export_unknowns(
        rows,
        domain="ai",
        profile_name="humanity_default",
        literature_backend="none",
        delivery="stdout",
    )
    assert doc["format"] == FORMAT_ID
    assert doc["format_version"] == 1
    assert doc["package_version"] == "0.4.1"
    assert doc["webhooks"] is False
    assert doc["changes_ranks"] is False
    assert doc["delivery"] == "stdout"
    assert doc["count"] == 2
    assert doc["questions"] == rows
    assert "SSRF" in doc["honesty"]
    assert "decision aid" in doc["honesty"].lower() or "decision aids" in doc["honesty"].lower()
    assert "not oracles" in doc["honesty"]
    assert "ValueProfile" in doc["honesty"]
    blob = json.dumps(doc).lower()
    assert "feels" not in blob


def test_export_unknowns_accepts_rankedquestion_objects():
    items = _offline_engine(2).run()
    doc = export_unknowns(items, domain="ai", delivery="file")
    assert doc["count"] == 2
    assert doc["questions"][0]["question"]["question"]
    assert doc["delivery"] == "file"


def test_export_unknowns_rejects_empty():
    with pytest.raises(ValueError, match="at least one"):
        export_unknowns([])


def test_reject_webhook_fields_fail_closed():
    with pytest.raises(ValueError, match="SSRF"):
        reject_webhook_fields({"webhook_url": "http://127.0.0.1:9/steal"})
    with pytest.raises(ValueError, match="SSRF"):
        reject_webhook_fields({"callback_url": "https://evil.example/hook"})
    reject_webhook_fields({})
    reject_webhook_fields({"webhook_url": ""})


def test_export_module_does_not_import_http_clients():
    src = Path(__file__).resolve().parents[1] / "src" / "artificial_emotions" / "export_unknowns.py"
    text = src.read_text(encoding="utf-8")
    for needle in ("import httpx", "import requests", "urllib.request", "urllib3"):
        assert needle not in text


def test_write_unknowns_export_roundtrip(tmp_path: Path):
    doc = export_unknowns(_ranked_dicts(1), domain="ai", delivery="file")
    path = write_unknowns_export(doc, tmp_path / "nested" / "unknowns.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["questions"] == doc["questions"]
    assert loaded["webhooks"] is False


def test_coerce_ranked_questions_from_run_envelope():
    rows = _ranked_dicts(1)
    assert coerce_ranked_questions(rows) == rows
    assert coerce_ranked_questions({"questions": rows, "count": 1}) == rows
    assert coerce_ranked_questions({"unknowns": [{"question": "Which mechanism remains open?"}]})[
        0
    ]["question"].startswith("Which")
    with pytest.raises(ValueError, match="questions"):
        coerce_ranked_questions({"count": 0})


def test_cli_export_unknowns_json(capsys):
    rc = main(["export", "unknowns", "--domain", "ai", "--n", "2", "--no-literature", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["format"] == FORMAT_ID
    assert payload["webhooks"] is False
    assert payload["delivery"] == "stdout"
    assert payload["count"] >= 1
    assert payload["questions"][0]["question"]["question"]
    assert payload["literature_backend"] == "none"


def test_cli_export_unknowns_out_file(tmp_path: Path, capsys):
    dest = tmp_path / "set.json"
    rc = main(
        [
            "export",
            "unknowns",
            "--domain",
            "ai",
            "--n",
            "2",
            "--no-literature",
            "--out",
            str(dest),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert str(dest) in out
    saved = json.loads(dest.read_text(encoding="utf-8"))
    assert saved["delivery"] == "file"
    assert saved["count"] >= 1
    assert saved["webhooks"] is False


def test_cli_export_unknowns_from_reuses_run_json(tmp_path: Path, capsys):
    ranked = _ranked_dicts(2)
    src = tmp_path / "run.json"
    src.write_text(json.dumps(ranked), encoding="utf-8")
    rc = main(["export", "unknowns", "--from", str(src), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["questions"] == ranked
    assert payload["changes_ranks"] is False


def test_cli_export_rejects_webhook_flag():
    with pytest.raises(SystemExit):
        main(["export", "unknowns", "--json", "--webhook", "http://127.0.0.1:9/x"])


def test_cli_export_without_subcommand_is_usage():
    assert main(["export"]) == 2


def test_parser_wires_export_unknowns():
    parser = build_parser()
    names = set()
    for action in parser._actions:
        if getattr(action, "dest", None) == "command" and hasattr(action, "choices"):
            names = set(action.choices)
    assert "export" in names


def test_http_export_unknowns_reuses_run_output():
    client = TestClient(app)
    run = client.post(
        "/v1/curiosity/run",
        json={
            "domain": "ai",
            "n_return": 2,
            "n_candidates": 8,
            "use_literature": False,
            "use_llm": False,
        },
    )
    assert run.status_code == 200
    questions = run.json()["questions"]
    res = client.post(
        "/v1/export/unknowns",
        json={
            "questions": questions,
            "domain": "ai",
            "profile_name": "humanity_default",
            "literature_backend": "none",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["format"] == FORMAT_ID
    assert body["delivery"] == "http_body"
    assert body["webhooks"] is False
    assert body["questions"] == questions
    assert "llm_base_url" not in body
    assert "webhook_url" not in body


def test_http_rejects_webhook_url_ssrf(monkeypatch):
    client = TestClient(app)
    rows = _ranked_dicts(1)
    calls: list[tuple] = []

    def _boom(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("outbound fetch must not run")

    monkeypatch.setattr("urllib.request.urlopen", _boom)
    res = client.post(
        "/v1/export/unknowns",
        json={
            "questions": rows,
            "webhook_url": "http://127.0.0.1:9/steal",
        },
    )
    assert res.status_code in (400, 422)
    blob = json.dumps(res.json()).lower()
    assert "webhook" in blob or "ssrf" in blob
    assert calls == []


def test_http_rejects_out_path_injection():
    client = TestClient(app)
    res = client.post(
        "/v1/export/unknowns",
        json={"questions": _ranked_dicts(1), "out_path": "/tmp/evil.json"},
    )
    assert res.status_code in (400, 422)
    assert "path" in json.dumps(res.json()).lower() or "file" in json.dumps(res.json()).lower()


def test_http_ignores_llm_base_url_on_export():
    assert "llm_base_url" not in ExportUnknownsRequest.model_fields
    assert "literature_cache_dir" not in ExportUnknownsRequest.model_fields
    assert "llm_base_url" not in RunRequest.model_fields
    client = TestClient(app)
    res = client.post(
        "/v1/export/unknowns",
        json={
            "questions": _ranked_dicts(1),
            "llm_base_url": "http://127.0.0.1:9/steal",
            "literature_cache_dir": "/tmp/evil-cache",
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert "llm_base_url" not in body
    assert body["webhooks"] is False


def test_export_unknowns_request_trap_fields():
    rows = _ranked_dicts(1)
    with pytest.raises(ValidationError):
        ExportUnknownsRequest(questions=rows, webhook_url="http://example.com/hook")
    with pytest.raises(ValidationError):
        ExportUnknownsRequest(questions=rows, out_path="out.json")


def test_http_requires_questions():
    client = TestClient(app)
    res = client.post("/v1/export/unknowns", json={"domain": "ai"})
    assert res.status_code == 422


def test_mcp_export_unknowns_wraps_inline_questions():
    rows = _ranked_dicts(1)
    names = {t["name"] for t in mcp_tool_list()}
    assert "export_unknowns" in names
    assert lint_tool_specs(mcp_tool_list()) == []
    out = dispatch_tool("export_unknowns", {"questions": rows, "domain": "ai"})
    assert out["questions"] == rows
    assert out["webhooks"] is False
    assert out["delivery"] == "http_body"


def test_mcp_export_unknowns_rejects_webhook_kwarg():
    with pytest.raises(ValueError, match="SSRF"):
        dispatch_tool(
            "export_unknowns",
            {
                "questions": _ranked_dicts(1),
                "webhook_url": "http://127.0.0.1:9/x",
            },
        )


def test_agent_card_and_tools_mention_export():
    client = TestClient(app)
    agent = client.get("/v1/agent").json()
    assert "export_unknowns" in json.dumps(agent)
    tools = client.get("/v1/agent/tools").json()
    assert tools["http_fallbacks"]["export_unknowns"] == "POST /v1/export/unknowns"
    names = {t["function"]["name"] for t in tools["tools"]}
    assert "export_unknowns" in names
