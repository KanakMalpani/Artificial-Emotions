"""Extra error-path coverage for emotions + API auth/validation."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from artificial_curiosity import CuriosityError, mix_emotions
from artificial_curiosity.api import app
from artificial_curiosity.config import clear_config_cache
from artificial_curiosity.errors import (
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


def test_api_mix_validation_empty_weights():
    client = TestClient(app)
    bad = client.post("/v1/emotions/mix", json={"weights": {}})
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_error"
