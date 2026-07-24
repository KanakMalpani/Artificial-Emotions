"""Tests for provider-agnostic LLM resolution and provoke packs."""

from __future__ import annotations

from fastapi.testclient import TestClient

from artificial_curiosity.api import app
from artificial_curiosity.llm import _extract_json, resolve_llm_settings
from artificial_curiosity.provoke import provoke


def test_extract_json_from_fenced_block():
    raw = 'Here you go:\n```json\n{"a": 1}\n```\n'
    assert _extract_json(raw) == {"a": 1}


def test_resolve_llm_settings_prefers_llm_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k-llm")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("LLM_MODEL", "llama3.2")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = resolve_llm_settings()
    assert s is not None
    assert s.api_key == "k-llm"
    assert "11434" in s.base_url
    assert s.model == "llama3.2"


def test_resolve_llm_settings_local_without_key(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    s = resolve_llm_settings(base_url="http://127.0.0.1:1234/v1", model="local-model")
    assert s is not None
    assert s.api_key == "local"


def test_provoke_fast_returns_inject():
    pack = provoke(domain="ai", n=3, fast=True)
    assert pack["count"] >= 1
    assert pack["mode"] == "fast"
    assert "What should we investigate next?" in pack["inject"]
    assert pack["spark"]
    assert pack["unknowns"][0]["question"]
    assert "how_to_use_with_any_model" in pack


def test_api_provoke_get():
    client = TestClient(app)
    res = client.get("/v1/curiosity/provoke", params={"domain": "ai", "n": 3, "fast": True})
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 1
    assert "inject" in data


def test_api_agent_manifest():
    client = TestClient(app)
    res = client.get("/v1/agent")
    assert res.status_code == 200
    data = res.json()
    assert data["instant_spark"]["path"] == "/v1/curiosity/provoke"
    assert "openai" in data["any_provider"]["examples"]
    assert "LLM_JUDGE_MODEL" in data["any_provider"]["env"]


def test_api_profiles_list():
    client = TestClient(app)
    res = client.get("/v1/profiles")
    assert res.status_code == 200
    names = {p["name"] for p in res.json()["presets"]}
    assert "funder_10y" in names
    assert "alignment_lab" in names


def test_api_provoke_with_profile_name():
    client = TestClient(app)
    res = client.get(
        "/v1/curiosity/provoke",
        params={"domain": "ai", "n": 2, "fast": True, "profile_name": "funder_10y"},
    )
    assert res.status_code == 200
    assert res.json()["value_profile"]["name"] == "funder_10y"


def test_resolve_judge_model_env(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "k")
    monkeypatch.setenv("LLM_MODEL", "gen-model")
    monkeypatch.setenv("LLM_JUDGE_MODEL", "judge-model")
    s = resolve_llm_settings(judge=True)
    assert s is not None
    assert s.model == "judge-model"
    s2 = resolve_llm_settings(judge=False)
    assert s2 is not None
    assert s2.model == "gen-model"


def test_optional_api_key_auth(monkeypatch):
    from artificial_curiosity.config import clear_config_cache

    client = TestClient(app)
    # Disabled by default — health and provoke open.
    assert client.get("/health").status_code == 200
    assert client.get("/v1/curiosity/provoke", params={"n": 1, "fast": True}).status_code == 200

    monkeypatch.setenv("CURIOSITY_API_KEY", "test-secret-key")
    clear_config_cache()
    # Health stays open; protected routes need key.
    assert client.get("/health").json()["api_auth_required"] is True
    denied = client.get("/v1/curiosity/provoke", params={"n": 1, "fast": True})
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "auth_required"
    ok = client.get(
        "/v1/curiosity/provoke",
        params={"n": 1, "fast": True},
        headers={"X-API-Key": "test-secret-key"},
    )
    assert ok.status_code == 200
    ok2 = client.get(
        "/v1/profiles",
        headers={"Authorization": "Bearer test-secret-key"},
    )
    assert ok2.status_code == 200
    # Wrong-length key must 401 (never 500 from compare_digest).
    wrong_len = client.get(
        "/v1/profiles",
        headers={"X-API-Key": "short"},
    )
    assert wrong_len.status_code == 401
    # startswith("/docs") footgun: /docsEvil stays protected.
    evil = client.get("/docsEvil")
    assert evil.status_code == 401
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    clear_config_cache()


def test_health_redacts_llm_base_url(monkeypatch):
    from artificial_curiosity.config import clear_config_cache

    monkeypatch.setenv("LLM_API_KEY", "dummy")
    monkeypatch.setenv("LLM_BASE_URL", "https://secret-host.example/v1")
    clear_config_cache()
    client = TestClient(app)
    h = client.get("/health").json()
    assert h["llm_base_url"] == "https://[redacted]"
    assert "secret-host" not in (h["llm_base_url"] or "")
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    clear_config_cache()
