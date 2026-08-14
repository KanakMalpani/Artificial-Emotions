"""Opt-in JSONL audit: HTTP/MCP names + status, never bodies or keys."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from artificial_emotions.api import create_app
from artificial_emotions.api_pkg.audit import record_audit
from artificial_emotions.config import audit_log_path, clear_config_cache, get_config
from artificial_emotions.mcp_server import handle_message

# Distinctive fixture string — tests assert it never appears in the log file.
_KEY = "audit-fixture-key-must-not-appear"
_FORBIDDEN_FIELDS = frozenset(
    {
        "body",
        "headers",
        "authorization",
        "arguments",
        "params",
        "query",
        "cookie",
        "api_key",
        "x-api-key",
    }
)


def _records(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _assert_safe(path: Path) -> None:
    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    assert _KEY not in raw
    assert "Bearer" not in raw
    for rec in _records(path):
        assert set(rec) == {"ts", "channel", "name", "status"}
        lowered = {k.lower() for k in rec}
        assert not (_FORBIDDEN_FIELDS & lowered)
        assert _KEY not in json.dumps(rec)


def test_audit_default_off(tmp_path, monkeypatch):
    monkeypatch.delenv("CURIOSITY_AUDIT_LOG", raising=False)
    clear_config_cache()
    assert audit_log_path() is None
    assert get_config().audit_log_enabled is False
    client = TestClient(create_app())
    assert client.get("/v1/domains").status_code == 200
    assert list(tmp_path.iterdir()) == []


def test_audit_empty_env_is_off(monkeypatch):
    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", "   ")
    clear_config_cache()
    assert audit_log_path() is None
    assert get_config().audit_log_enabled is False


def test_audit_http_logs_name_and_status(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", str(log))
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    clear_config_cache()
    client = TestClient(create_app())
    assert client.get("/v1/domains").status_code == 200
    recs = _records(log)
    assert len(recs) == 1
    assert recs[0]["channel"] == "http"
    assert recs[0]["name"] == "GET /v1/domains"
    assert recs[0]["status"] == 200
    _assert_safe(log)


def test_audit_records_rate_limit_429(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", str(log))
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "0")
    clear_config_cache()
    client = TestClient(create_app())
    assert client.get("/v1/domains").status_code == 200
    denied = client.get("/v1/domains")
    assert denied.status_code == 429
    statuses = [r["status"] for r in _records(log)]
    assert 200 in statuses
    assert 429 in statuses
    _assert_safe(log)


def test_audit_skips_open_probe_paths(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", str(log))
    clear_config_cache()
    client = TestClient(create_app())
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/").status_code == 200
    assert not log.exists()


def test_audit_strips_query_and_never_logs_bodies_or_keys(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", str(log))
    monkeypatch.setenv("CURIOSITY_API_KEY", _KEY)
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "0")
    clear_config_cache()
    client = TestClient(create_app())

    denied = client.get(f"/v1/domains?api_key={_KEY}")
    assert denied.status_code == 401
    ok = client.get(
        f"/v1/domains?api_key={_KEY}",
        headers={"Authorization": f"Bearer {_KEY}"},
    )
    assert ok.status_code == 200
    mix = client.post(
        "/v1/emotions/mix",
        headers={"Authorization": f"Bearer {_KEY}", "X-API-Key": _KEY},
        json={"weights": {"curiosity": 100}, "api_key": _KEY},
    )
    assert mix.status_code in (200, 400, 422)

    raw = log.read_text(encoding="utf-8")
    assert _KEY not in raw
    assert "Bearer" not in raw
    assert "weights" not in raw
    recs = _records(log)
    assert recs
    names = {r["name"] for r in recs}
    assert "GET /v1/domains" in names
    assert all("?" not in r["name"] for r in recs)
    assert any(r["status"] == 401 for r in recs)
    _assert_safe(log)


def test_health_reports_audit_flag_not_path(tmp_path, monkeypatch):
    log = tmp_path / "nested" / "audit.jsonl"
    monkeypatch.delenv("CURIOSITY_AUDIT_LOG", raising=False)
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    clear_config_cache()
    off = TestClient(create_app()).get("/health").json()
    assert off["audit_log_enabled"] is False
    assert str(log) not in json.dumps(off)

    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", str(log))
    clear_config_cache()
    on = TestClient(create_app()).get("/health").json()
    assert on["audit_log_enabled"] is True
    blob = json.dumps(on)
    assert str(log) not in blob
    assert "audit.jsonl" not in blob


def test_agent_card_describes_opt_in_audit():
    data = TestClient(create_app()).get("/v1/agent").json()
    honesty = " ".join(data.get("honesty") or [])
    assert "CURIOSITY_AUDIT_LOG" in honesty
    audit = data["audit"]
    assert audit["opt_in_env"] == "CURIOSITY_AUDIT_LOG"
    assert audit["default"] == "off"
    assert "bodies" in audit["never"]


def test_mcp_audit_logs_tool_name_not_arguments(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", str(log))
    clear_config_cache()
    res = handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "list_domains",
                "arguments": {"api_key": _KEY, "secret": _KEY},
            },
        }
    )
    assert res is not None
    assert res["result"]["isError"] is False
    recs = _records(log)
    assert len(recs) == 1
    assert recs[0]["channel"] == "mcp"
    assert recs[0]["name"] == "list_domains"
    assert recs[0]["status"] == "ok"
    _assert_safe(log)

    handle_message(
        {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {"name": "not_a_tool", "arguments": {"api_key": _KEY}},
        }
    )
    recs = _records(log)
    assert recs[-1]["name"] == "not_a_tool"
    assert recs[-1]["status"] == "error"
    _assert_safe(log)


def test_mcp_does_not_audit_when_off(tmp_path, monkeypatch):
    monkeypatch.delenv("CURIOSITY_AUDIT_LOG", raising=False)
    clear_config_cache()
    handle_message(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "list_domains", "arguments": {}},
        }
    )
    assert list(tmp_path.iterdir()) == []


def test_record_audit_fail_soft_does_not_break_http(tmp_path, monkeypatch):
    blocked = tmp_path / "blocked"
    blocked.write_text("not-a-dir", encoding="utf-8")
    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", str(blocked / "audit.jsonl"))
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    clear_config_cache()
    client = TestClient(create_app())
    assert client.get("/v1/domains").status_code == 200


def test_record_audit_rejects_extra_status_and_channel(tmp_path, monkeypatch):
    log = tmp_path / "audit.jsonl"
    monkeypatch.setenv("CURIOSITY_AUDIT_LOG", str(log))
    record_audit(channel="cli", name="list_domains", status="ok")
    record_audit(channel="mcp", name="list_domains", status="nope")
    record_audit(channel="mcp", name="list_domains", status=True)
    record_audit(channel="mcp", name="", status="ok")
    assert not log.exists()
    record_audit(channel="mcp", name="list_domains", status="ok")
    recs = _records(log)
    assert len(recs) == 1
    assert recs[0]["name"] == "list_domains"
