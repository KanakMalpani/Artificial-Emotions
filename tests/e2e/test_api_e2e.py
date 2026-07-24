"""API end-to-end journeys via FastAPI TestClient (no live server required)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from artificial_curiosity.api import app

pytestmark = pytest.mark.e2e


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_to_domains_to_agent_tools(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    body = health.json()
    assert body["ok"] is True
    assert body["service"] == "artificial-curiosity"
    assert "profiles" in body

    root = client.get("/")
    assert root.status_code == 200
    assert "provoke" in root.json()

    domains = client.get("/v1/domains")
    assert domains.status_code == 200
    names = set(domains.json()["domains"])
    assert {"ai", "biology", "physics", "climate"}.issubset(names)

    profiles = client.get("/v1/profiles")
    assert profiles.status_code == 200
    preset_names = {p["name"] for p in profiles.json()["presets"]}
    assert "humanity_default" in preset_names
    assert "funder_10y" in preset_names

    agent = client.get("/v1/agent")
    assert agent.status_code == 200
    assert agent.json()["instant_spark"]["path"] == "/v1/curiosity/provoke"

    tools = client.get("/v1/agent/tools")
    assert tools.status_code == 200
    payload = tools.json()
    assert payload["format"] == "openai.tools"
    assert payload["count"] >= 1
    assert payload["tools"]


def test_provoke_fast_then_run_offline(client: TestClient) -> None:
    provoke = client.get(
        "/v1/curiosity/provoke",
        params={"domain": "ai", "n": 3, "fast": True, "profile_name": "alignment_lab"},
    )
    assert provoke.status_code == 200
    pack = provoke.json()
    assert pack["count"] >= 1
    assert pack["mode"] == "fast"
    assert "inject" in pack and "What should we investigate next?" in pack["inject"]
    assert pack["value_profile"]["name"] == "alignment_lab"
    assert pack["unknowns"][0]["question"]

    run = client.post(
        "/v1/curiosity/run",
        json={
            "domain": "ai",
            "n_return": 3,
            "n_candidates": 8,
            "use_literature": False,
            "use_llm": False,
            "profile_name": "humanity_default",
        },
    )
    assert run.status_code == 200
    data = run.json()
    assert data["count"] >= 1
    assert data["literature_backend"] == "none"
    assert data["value_profile"]["name"] == "humanity_default"
    q0 = data["questions"][0]
    assert q0["question"]["question"]
    assert "curiosity_score" in q0
    assert q0["gap"]["status"]
    flags = q0.get("flags") or []
    assert "no_literature" in flags or data["literature_backend"] == "none"


def test_emotions_surface_e2e(client: TestClient) -> None:
    cues = client.get("/v1/emotions/cues")
    assert cues.status_code == 200
    assert "information_gap" in cues.json()["tags"]
    assert cues.json()["honesty"] == "annotation_only"

    ann = client.post(
        "/v1/emotions/annotate",
        json={
            "question": "What remains unknown about epistemic emotion elicitation?",
            "surprise": 0.8,
            "gap_status": "unanswered",
            "notes": "Related literature ≠ answered.",
        },
    )
    assert ann.status_code == 200
    body = ann.json()
    assert body["epistemic_cues"]["tags"]
    assert "feel" in body["disclaimer"].lower()

    assert client.get("/v1/epistemic/elicit").status_code == 200
    pack = client.get("/v1/emotions/pack", params={"name": "affective_science"})
    assert pack.status_code == 200
    assert pack.json()["count"] >= 8

    agent = client.get("/v1/agent").json()
    assert "emotions" in agent
    assert "list_epistemic_cues" in agent["mcp"]["tools"]


def test_provoke_post_and_multi_domain(client: TestClient) -> None:
    post = client.post(
        "/v1/curiosity/provoke",
        json={"domain": "biology", "n": 2, "fast": True},
    )
    assert post.status_code == 200
    assert post.json()["count"] >= 1

    for domain in ("physics", "climate", "energy"):
        res = client.get(
            "/v1/curiosity/provoke",
            params={"domain": domain, "n": 2, "fast": True},
        )
        assert res.status_code == 200, domain
        assert res.json()["count"] >= 1, domain


@pytest.mark.slow
def test_api_run_literature_optional(client: TestClient) -> None:
    """Optional OpenAlex path — skips when no related works (offline / rate-limit)."""
    res = client.post(
        "/v1/curiosity/run",
        json={
            "domain": "ai",
            "n_return": 2,
            "n_candidates": 4,
            "use_literature": True,
            "use_llm": False,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["count"] >= 1
    related = any((q.get("gap") or {}).get("related_works") for q in data["questions"])
    if not related:
        pytest.skip(
            "No OpenAlex hits (offline or rate-limited); fast-path e2e covers offline"
        )
    assert data["literature_backend"] == "openalex"
