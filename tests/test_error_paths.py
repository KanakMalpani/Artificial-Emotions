"""Extra error-path coverage for emotions + API auth/validation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from artificial_emotions import CuriosityError, mix_emotions
from artificial_emotions.api import ExportUnknownsRequest, ProvokeRequest, RunRequest, app
from artificial_emotions.config import clear_config_cache
from artificial_emotions.errors import (
    ERR_AUTH_REQUIRED,
    ERR_EMPTY_MIX,
    ERR_UNKNOWN_EMOTION,
)


def test_mix_emotions_raises_typed_codes():
    with pytest.raises(CuriosityError) as ei:
        mix_emotions({"not_a_real_emotion": 100})
    assert ei.value.code == ERR_UNKNOWN_EMOTION

    with pytest.raises(CuriosityError) as ei2:
        mix_emotions({"curiosity": 0, "awe": 0})
    assert ei2.value.code == ERR_EMPTY_MIX


def test_api_mix_unknown_emotion_error_shape():
    client = TestClient(app)
    bad = client.post("/v1/emotions/mix", json={"weights": {"nope": 100}})
    assert bad.status_code == 400
    body = bad.json()
    assert body["error"]["code"] == ERR_UNKNOWN_EMOTION
    assert "message" in body["error"]


def test_api_mix_negative_weight():
    client = TestClient(app)
    bad = client.post(
        "/v1/emotions/mix",
        json={"weights": {"curiosity": -5}},
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "negative_weight"


def test_api_catalog_unknown_family():
    client = TestClient(app)
    bad = client.get("/v1/emotions/catalog", params={"family": "not_a_family"})
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "unknown_family"


def test_api_auth_reject_error_code(monkeypatch):
    clear_config_cache()
    monkeypatch.setenv("CURIOSITY_API_KEY", "test-secret-key")
    clear_config_cache()
    client = TestClient(app)
    denied = client.get("/v1/curiosity/provoke", params={"n": 1, "fast": True})
    assert denied.status_code == 401
    body = denied.json()
    assert body["error"]["code"] == ERR_AUTH_REQUIRED
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    clear_config_cache()


def test_health_and_ready_detail():
    client = TestClient(app)
    health = client.get("/health")
    assert health.status_code == 200
    h = health.json()
    assert h["ok"] is True
    assert "version" in h
    assert "llm_timeout_s" in h
    assert "api_auth_required" in h

    ready = client.get("/ready")
    assert ready.status_code == 200
    r = ready.json()
    assert r["ready"] is True
    assert r["checks"]["emotion_catalog"] is True
    assert r["checks"]["profiles"] is True


def test_ready_returns_503_when_checks_fail(monkeypatch):
    # Patch where /ready resolves the symbol, i.e. the router module it lives in.
    from artificial_emotions.api_pkg.routers import meta as meta_router

    monkeypatch.setattr(
        meta_router,
        "emotion_catalog",
        lambda **_kw: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    client = TestClient(app)
    ready = client.get("/ready")
    assert ready.status_code == 503
    body = ready.json()
    assert body["ready"] is False
    assert body["ok"] is False
    assert body["checks"]["emotion_catalog"] is False


def test_http_ignores_cache_dir_and_client_llm_base_url():
    """HTTP must not accept path/SSRF knobs (CLI/env only)."""
    assert "literature_cache_dir" not in RunRequest.model_fields
    assert "llm_base_url" not in RunRequest.model_fields
    assert "llm_base_url" not in ProvokeRequest.model_fields
    assert "llm_base_url" not in ExportUnknownsRequest.model_fields
    assert "literature_cache_dir" not in ExportUnknownsRequest.model_fields

    client = TestClient(app)
    # Extra body fields are ignored; must not mkdir or call attacker URL.
    run = client.post(
        "/v1/curiosity/run",
        json={
            "domain": "ai",
            "n_return": 2,
            "n_candidates": 8,
            "use_literature": False,
            "use_llm": False,
            "literature_cache_dir": "/tmp/evil-cache",
            "llm_base_url": "http://127.0.0.1:9/steal",
        },
    )
    assert run.status_code == 200
    assert "literature_cache_dir" not in run.json()["query"]
    assert "llm_base_url" not in run.json()["query"]


def test_api_mix_validation_empty_weights():
    client = TestClient(app)
    bad = client.post("/v1/emotions/mix", json={"weights": {}})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_error"
