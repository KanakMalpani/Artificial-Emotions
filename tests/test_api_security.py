"""Focused tests for Wave 1 serve hardening: rate limit, quota, CORS defaults."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from artificial_emotions.api import create_app
from artificial_emotions.cli import main
from artificial_emotions.config import (
    allow_nonlocal_bind,
    api_quota_requests,
    api_quota_window_s,
    api_rate_limit_per_minute,
    bind_is_loopback,
    clear_config_cache,
    cors_origins,
    get_config,
    refuse_nonlocal_bind_reason,
    resolve_serve_bind,
    serve_host,
    serve_port,
)
from artificial_emotions.errors import ERR_QUOTA_EXCEEDED, ERR_RATE_LIMITED


def test_cors_origins_default_deny(monkeypatch):
    monkeypatch.delenv("CURIOSITY_CORS_ORIGINS", raising=False)
    clear_config_cache()
    assert cors_origins() == []
    assert list(get_config().cors_origins) == []


def test_cors_origins_opt_in_list(monkeypatch):
    monkeypatch.setenv(
        "CURIOSITY_CORS_ORIGINS",
        "http://127.0.0.1:3000, https://example.com",
    )
    clear_config_cache()
    assert cors_origins() == ["http://127.0.0.1:3000", "https://example.com"]
    monkeypatch.delenv("CURIOSITY_CORS_ORIGINS", raising=False)
    clear_config_cache()


def test_cors_origins_star_still_allowed(monkeypatch):
    monkeypatch.setenv("CURIOSITY_CORS_ORIGINS", "*")
    clear_config_cache()
    assert cors_origins() == ["*"]
    monkeypatch.delenv("CURIOSITY_CORS_ORIGINS", raising=False)
    clear_config_cache()


def test_health_reports_empty_cors_by_default(monkeypatch):
    monkeypatch.delenv("CURIOSITY_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    clear_config_cache()
    client = TestClient(create_app())
    h = client.get("/health").json()
    assert h["cors_origins"] == []
    assert h["api_auth_required"] is False
    assert client.get("/").status_code == 200
    assert client.get("/ready").status_code == 200
    assert client.get("/v1/agent").status_code == 200


def test_rate_limit_burst_returns_429(monkeypatch):
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "3")
    clear_config_cache()
    assert api_rate_limit_per_minute() == 3
    client = TestClient(create_app())
    for _ in range(3):
        assert client.get("/v1/domains").status_code == 200
    denied = client.get("/v1/domains")
    assert denied.status_code == 429
    assert denied.headers.get("Retry-After")
    body = denied.json()
    assert body["error"]["code"] == ERR_RATE_LIMITED
    # Probe paths match auth open list — never rate-limited.
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()


def test_agent_card_points_at_local_threat_model():
    client = TestClient(create_app())
    data = client.get("/v1/agent").json()
    honesty = " ".join(data.get("honesty") or [])
    assert "THREAT_MODEL" in honesty
    assert "production SLO" in honesty
    assert "CURIOSITY_API_QUOTA_REQUESTS" in honesty
    assert "CURIOSITY_ALLOW_NONLOCAL_BIND" in honesty
    assert "quota not shipped" not in honesty
    assert data.get("threat_model") == "docs/THREAT_MODEL.md"


def test_threat_model_doc_lists_quota_and_audit_as_shipped():
    text = (Path(__file__).resolve().parents[1] / "docs" / "THREAT_MODEL.md").read_text(
        encoding="utf-8"
    )
    lowered = text.lower()
    assert "not implemented" not in lowered
    assert "quota not shipped" not in lowered
    assert "future knobs" not in lowered
    assert "CURIOSITY_API_QUOTA" in text
    assert "CURIOSITY_AUDIT_LOG" in text
    assert "CURIOSITY_ALLOW_NONLOCAL_BIND" in text
    assert "local-v1" in lowered
    assert "not a production slo" in lowered
    assert "0.0.0.0" in text


def test_rate_limit_zero_disables(monkeypatch):
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
    clear_config_cache()
    assert api_rate_limit_per_minute() == 0
    client = TestClient(create_app())
    for _ in range(25):
        assert client.get("/v1/domains").status_code == 200
    assert client.get("/v1/agent").status_code == 200
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()


def test_quota_unset_keeps_local_dx(monkeypatch):
    monkeypatch.delenv("CURIOSITY_API_QUOTA_REQUESTS", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_WINDOW_S", raising=False)
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    monkeypatch.delenv("CURIOSITY_API_KEYS", raising=False)
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
    clear_config_cache()
    assert api_quota_requests() == 0
    client = TestClient(create_app())
    for _ in range(25):
        assert client.get("/v1/domains").status_code == 200
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()


def test_quota_window_defaults_to_day(monkeypatch):
    monkeypatch.delenv("CURIOSITY_API_QUOTA_WINDOW_S", raising=False)
    clear_config_cache()
    assert api_quota_window_s() == 86400
    monkeypatch.setenv("CURIOSITY_API_QUOTA_WINDOW_S", "0")
    clear_config_cache()
    assert api_quota_window_s() == 86400
    monkeypatch.setenv("CURIOSITY_API_QUOTA_WINDOW_S", "3600")
    clear_config_cache()
    assert api_quota_window_s() == 3600
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "12")
    clear_config_cache()
    cfg = get_config()
    assert cfg.api_quota_requests == 12
    assert cfg.api_quota_window_s == 3600
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "nope")
    clear_config_cache()
    assert api_quota_requests() == 0
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "-3")
    clear_config_cache()
    assert api_quota_requests() == 0
    monkeypatch.delenv("CURIOSITY_API_QUOTA_WINDOW_S", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_REQUESTS", raising=False)
    clear_config_cache()


def test_quota_without_keys_is_a_no_op(monkeypatch):
    """Per-key budget needs a matched key; open local serve stays un-quota'd."""
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    monkeypatch.delenv("CURIOSITY_API_KEYS", raising=False)
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "2")
    monkeypatch.setenv("CURIOSITY_API_QUOTA_WINDOW_S", "60")
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
    clear_config_cache()
    assert api_quota_requests() == 2
    client = TestClient(create_app())
    for _ in range(8):
        assert client.get("/v1/domains").status_code == 200
    monkeypatch.delenv("CURIOSITY_API_QUOTA_REQUESTS", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_WINDOW_S", raising=False)
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()


def test_quota_burst_returns_429(monkeypatch):
    monkeypatch.setenv("CURIOSITY_API_KEY", "quota-key")
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "2")
    monkeypatch.setenv("CURIOSITY_API_QUOTA_WINDOW_S", "60")
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
    clear_config_cache()
    headers = {"Authorization": "Bearer quota-key"}
    client = TestClient(create_app())
    assert client.get("/v1/domains", headers=headers).status_code == 200
    assert client.get("/v1/domains", headers=headers).status_code == 200
    denied = client.get("/v1/domains", headers=headers)
    assert denied.status_code == 429
    assert denied.headers.get("Retry-After")
    body = denied.json()
    assert body["error"]["code"] == ERR_QUOTA_EXCEEDED
    details = body["error"]["details"]
    assert details["limit"] == 2
    assert details["window_s"] == 60
    assert details["scope"] == "api_key"
    assert "quota-key" not in denied.text
    # Probe paths stay reachable; they do not consume quota.
    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_REQUESTS", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_WINDOW_S", raising=False)
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()


def test_quota_is_independent_per_key(monkeypatch):
    monkeypatch.setenv("CURIOSITY_API_KEYS", "key-a,key-b")
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "1")
    monkeypatch.setenv("CURIOSITY_API_QUOTA_WINDOW_S", "60")
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
    clear_config_cache()
    client = TestClient(create_app())
    a = {"X-API-Key": "key-a"}
    b = {"X-API-Key": "key-b"}
    assert client.get("/v1/domains", headers=a).status_code == 200
    denied_a = client.get("/v1/domains", headers=a)
    assert denied_a.status_code == 429
    assert denied_a.json()["error"]["code"] == ERR_QUOTA_EXCEEDED
    assert client.get("/v1/domains", headers=b).status_code == 200
    monkeypatch.delenv("CURIOSITY_API_KEYS", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_REQUESTS", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_WINDOW_S", raising=False)
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()


def test_quota_does_not_bucket_unknown_keys(monkeypatch):
    monkeypatch.setenv("CURIOSITY_API_KEY", "real-key")
    monkeypatch.setenv("CURIOSITY_API_QUOTA_REQUESTS", "1")
    monkeypatch.setenv("CURIOSITY_API_QUOTA_WINDOW_S", "60")
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
    clear_config_cache()
    client = TestClient(create_app())
    for i in range(6):
        junk = client.get("/v1/domains", headers={"X-API-Key": f"forged-{i}"})
        assert junk.status_code == 401
    ok = client.get("/v1/domains", headers={"Authorization": "Bearer real-key"})
    assert ok.status_code == 200
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_REQUESTS", raising=False)
    monkeypatch.delenv("CURIOSITY_API_QUOTA_WINDOW_S", raising=False)
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()


def test_bind_is_loopback_accepts_localhost_variants():
    assert bind_is_loopback("127.0.0.1")
    assert bind_is_loopback("localhost")
    assert bind_is_loopback("LocalHost.")
    assert bind_is_loopback("::1")
    assert bind_is_loopback("[::1]")
    assert bind_is_loopback("127.0.0.2")


def test_bind_is_loopback_rejects_all_interfaces_and_lan():
    assert not bind_is_loopback("0.0.0.0")
    assert not bind_is_loopback("::")
    assert not bind_is_loopback("[::]")
    assert not bind_is_loopback("192.168.1.10")
    assert not bind_is_loopback("example.local")
    assert not bind_is_loopback("")


def test_zero_zero_zero_zero_requires_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("CURIOSITY_ALLOW_NONLOCAL_BIND", raising=False)
    assert allow_nonlocal_bind() is False
    reason = refuse_nonlocal_bind_reason("0.0.0.0")
    assert reason is not None
    assert "CURIOSITY_ALLOW_NONLOCAL_BIND" in reason
    assert "not TLS" in reason
    assert refuse_nonlocal_bind_reason("127.0.0.1") is None
    monkeypatch.setenv("CURIOSITY_ALLOW_NONLOCAL_BIND", "1")
    assert allow_nonlocal_bind() is True
    assert refuse_nonlocal_bind_reason("0.0.0.0") is None
    monkeypatch.setenv("CURIOSITY_ALLOW_NONLOCAL_BIND", "0")
    assert refuse_nonlocal_bind_reason("0.0.0.0") is not None


def test_resolve_serve_bind_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("CURIOSITY_HOST", raising=False)
    monkeypatch.delenv("CURIOSITY_PORT", raising=False)
    assert serve_host() == "127.0.0.1"
    assert serve_port() == 8000
    assert resolve_serve_bind(None, None) == ("127.0.0.1", 8000)
    assert resolve_serve_bind("0.0.0.0", 9000) == ("0.0.0.0", 9000)
    monkeypatch.setenv("CURIOSITY_HOST", "0.0.0.0")
    monkeypatch.setenv("CURIOSITY_PORT", "8123")
    assert resolve_serve_bind(None, None) == ("0.0.0.0", 8123)
    assert resolve_serve_bind("127.0.0.1", None) == ("127.0.0.1", 8123)


def test_serve_cli_refuses_0_0_0_0_without_opt_in(monkeypatch, capsys):
    monkeypatch.delenv("CURIOSITY_ALLOW_NONLOCAL_BIND", raising=False)
    started = {"n": 0}

    def _boom(*_a, **_k):
        started["n"] += 1
        raise AssertionError("uvicorn must not start")

    monkeypatch.setattr("uvicorn.run", _boom)
    rc = main(["serve", "--host", "0.0.0.0", "--port", "8000"])
    assert rc == 2
    assert started["n"] == 0
    err = capsys.readouterr().err
    assert "CURIOSITY_ALLOW_NONLOCAL_BIND" in err
    assert "0.0.0.0" in err


def test_serve_cli_refuses_curiosity_host_all_interfaces(monkeypatch, capsys):
    monkeypatch.delenv("CURIOSITY_ALLOW_NONLOCAL_BIND", raising=False)
    monkeypatch.setenv("CURIOSITY_HOST", "0.0.0.0")
    started = {"n": 0}

    def _boom(*_a, **_k):
        started["n"] += 1
        raise AssertionError("uvicorn must not start")

    monkeypatch.setattr("uvicorn.run", _boom)
    rc = main(["serve"])
    assert rc == 2
    assert started["n"] == 0
    assert "CURIOSITY_ALLOW_NONLOCAL_BIND" in capsys.readouterr().err


def test_serve_cli_loopback_reaches_uvicorn(monkeypatch, capsys):
    monkeypatch.delenv("CURIOSITY_ALLOW_NONLOCAL_BIND", raising=False)
    monkeypatch.delenv("CURIOSITY_HOST", raising=False)
    seen: dict[str, object] = {}

    def _fake_run(*_a, **kwargs):
        seen.update(kwargs)

    monkeypatch.setattr("uvicorn.run", _fake_run)
    rc = main(["serve", "--host", "127.0.0.1", "--port", "8765"])
    assert rc == 0
    assert seen.get("host") == "127.0.0.1"
    assert seen.get("port") == 8765
    assert "uvicorn must not" not in capsys.readouterr().err


def test_serve_cli_0_0_0_0_with_opt_in_reaches_uvicorn(monkeypatch, capsys):
    monkeypatch.setenv("CURIOSITY_ALLOW_NONLOCAL_BIND", "1")
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    monkeypatch.delenv("CURIOSITY_API_KEYS", raising=False)
    monkeypatch.delenv("ARTIFICIAL_CURIOSITY_API_KEY", raising=False)
    seen: dict[str, object] = {}

    def _fake_run(*_a, **kwargs):
        seen.update(kwargs)

    monkeypatch.setattr("uvicorn.run", _fake_run)
    rc = main(["serve", "--host", "0.0.0.0", "--port", "8123"])
    assert rc == 0
    assert seen.get("host") == "0.0.0.0"
    assert seen.get("port") == 8123
    err = capsys.readouterr().err
    assert "CURIOSITY_API_KEY" in err
    assert "not TLS" in err or "not production" in err
