"""Focused tests for Wave 1 serve hardening: rate limit + CORS defaults."""

from __future__ import annotations

from fastapi.testclient import TestClient

from artificial_emotions.api import create_app
from artificial_emotions.config import (
    api_rate_limit_per_minute,
    clear_config_cache,
    cors_origins,
    get_config,
)
from artificial_emotions.errors import ERR_RATE_LIMITED


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
        assert client.get("/health").status_code == 200
    denied = client.get("/health")
    assert denied.status_code == 429
    assert denied.headers.get("Retry-After")
    body = denied.json()
    assert body["error"]["code"] == ERR_RATE_LIMITED
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()


def test_rate_limit_zero_disables(monkeypatch):
    monkeypatch.setenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", "0")
    clear_config_cache()
    assert api_rate_limit_per_minute() == 0
    client = TestClient(create_app())
    for _ in range(25):
        assert client.get("/health").status_code == 200
    assert client.get("/v1/agent").status_code == 200
    monkeypatch.delenv("CURIOSITY_API_RATE_LIMIT_PER_MINUTE", raising=False)
    clear_config_cache()
