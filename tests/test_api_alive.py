"""Focused HTTP coverage for Alive surfaces: imagination, memory, dream, transfer."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from artificial_emotions.api import app
from artificial_emotions.imagine import HONESTY_IMAGINED, IMAGINED_PAYLOAD_KEY
from artificial_emotions.memory import ENV_NO_MEMORY, PersistentMemory

# Minimal structural corpus (same shape as tests/test_transfer.py unit corpus).
_TRANSFER_CORPUS = [
    {
        "year": 1979,
        "title": "Fish oil and blood viscosity",
        "concepts": ["Fish oil", "Blood viscosity"],
    },
    {
        "year": 1976,
        "title": "Blood viscosity in Raynaud's",
        "concepts": ["Blood viscosity", "Raynaud disease"],
    },
    {
        "year": 1980,
        "title": "Erythrocyte deformability and fish oil",
        "concepts": ["Fish oil", "Erythrocyte deformability"],
    },
    {
        "year": 1981,
        "title": "Erythrocyte deformability in Raynaud's",
        "concepts": ["Erythrocyte deformability", "Raynaud disease"],
    },
    {
        "year": 1981,
        "title": "Soil nitrogen in grassland",
        "concepts": ["Soil nitrogen", "Grassland ecology"],
    },
    {"year": 1983, "title": "Grazing and grassland", "concepts": ["Grassland ecology", "Grazing"]},
]


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("CURIOSITY_API_KEY", raising=False)
    monkeypatch.delenv(ENV_NO_MEMORY, raising=False)
    return TestClient(app)


def test_list_imagination_includes_transfer_ship_status(client: TestClient) -> None:
    res = client.get("/v1/imagination")
    assert res.status_code == 200
    body = res.json()
    assert body["count"] >= 1
    assert "implemented" in body
    assert body["honesty"] == HONESTY_IMAGINED
    transfer = body["transfer"]
    assert transfer["path"] == "/v1/imagination/transfer"
    assert transfer["ship_status"] in {"shipped", "cut"}
    kinds = {k["kind"] for k in body["kinds"]}
    assert "transfer" in kinds
    assert "premortem" in kinds


@pytest.mark.parametrize(
    "kind",
    [
        "premortem",
        "harm_scenario",
        "rehearsal",
        "eulogy",
        "reformulation",
        "counterfactual",
    ],
)
def test_apply_imagination_wired_kind(client: TestClient, kind: str) -> None:
    res = client.get(
        f"/v1/imagination/{kind}",
        params={"domain": "ai", "n": 4, "use_literature": False},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["honesty"] == HONESTY_IMAGINED
    assert body.get("kind") == kind
    assert IMAGINED_PAYLOAD_KEY in body
    assert body.get("confidence") is None
    # Quarantine: never under ranked keys.
    for banned in ("questions", "ranked", "items", "results"):
        assert banned not in body or not body[banned]


def test_apply_imagination_transfer_is_400_on_get(client: TestClient) -> None:
    """Transfer stays corpus-gated — GET apply path must refuse; use POST."""
    transfer = client.get("/v1/imagination/transfer", params={"n": 3})
    assert transfer.status_code == 400
    detail = transfer.json()["error"]
    assert detail["code"] == "validation_error"
    assert "POST" in detail["message"]
    assert detail["details"]["path"] == "POST /v1/imagination/transfer"


def test_imagination_transfer_inline_corpus(client: TestClient) -> None:
    res = client.post(
        "/v1/imagination/transfer",
        json={"seed": "Fish oil", "corpus": _TRANSFER_CORPUS},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["honesty"] == HONESTY_IMAGINED
    assert body.get("kind") == "transfer"
    assert IMAGINED_PAYLOAD_KEY in body
    assert body.get("confidence") is None


def test_imagination_transfer_requires_corpus(client: TestClient) -> None:
    res = client.post("/v1/imagination/transfer", json={"seed": "Fish oil"})
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "validation_error"


def test_memory_get_is_read_only(client: TestClient, tmp_path: Path) -> None:
    mem_path = tmp_path / "memory.json"
    assert not mem_path.exists()
    res = client.get("/v1/memory", params={"path": str(mem_path)})
    assert res.status_code == 200
    body = res.json()
    assert body["wrote"] is False
    assert body["disabled"] is False
    assert ENV_NO_MEMORY in body["note"] or ENV_NO_MEMORY in body["privacy"]
    assert "CURIOSITY_NO_MEMORY" in body["privacy"]
    assert not mem_path.exists(), "GET /v1/memory must not create the file"


def test_memory_forget_requires_confirm(client: TestClient, tmp_path: Path) -> None:
    mem_path = tmp_path / "memory.json"
    mem = PersistentMemory.load(mem_path)
    mem.record_session(domain="ai", topic="t", question_ids=["q1"], steps_taken=1)
    mem.save()
    assert mem_path.is_file()

    denied = client.post(
        "/v1/memory/forget",
        json={"what": "sessions", "confirm": False, "path": str(mem_path)},
    )
    assert denied.status_code == 400

    ok = client.post(
        "/v1/memory/forget",
        json={"what": "sessions", "confirm": True, "path": str(mem_path)},
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["forgot"] is True
    assert body["wrote"] is True


def test_memory_reset_and_avoiding(client: TestClient, tmp_path: Path) -> None:
    mem_path = tmp_path / "memory.json"
    mem = PersistentMemory.load(mem_path)
    mem.encounters = {"q_avoid": 8}
    mem.selections = {}
    mem.save()

    avoiding = client.post("/v1/memory/avoiding", json={"path": str(mem_path)})
    assert avoiding.status_code == 200
    av = avoiding.json()
    assert av["wrote"] is False
    assert av["count"] >= 1
    assert av["honesty"] == "pattern_not_motive"

    reset = client.post(
        "/v1/memory/reset",
        json={"confirm": True, "path": str(mem_path)},
    )
    assert reset.status_code == 200
    assert reset.json()["reset"] is True
    assert reset.json()["deleted_file"] is True
    assert not mem_path.exists()


def test_memory_respects_no_memory_env(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(ENV_NO_MEMORY, "1")
    mem_path = tmp_path / "memory.json"
    res = client.get("/v1/memory", params={"path": str(mem_path)})
    assert res.status_code == 200
    assert res.json()["disabled"] is True
    assert not mem_path.exists()


def test_dream_post_is_explicit_reanalysis(client: TestClient, tmp_path: Path) -> None:
    mem_path = tmp_path / "memory.json"
    mem = PersistentMemory.load(mem_path)
    mem.record_session(
        domain="ai",
        topic="x",
        question_ids=["q1"],
        dead_ends=["dead"],
        terms=["term"],
        steps_taken=2,
    )
    mem.save()

    res = client.post("/v1/dream", json={"path": str(mem_path)})
    assert res.status_code == 200
    body = res.json()
    assert body["wrote"] is False
    assert body.get("intent") == "reanalyze"
    framing = body.get("framing") or body.get("reanalysis_honesty") or ""
    assert "offline_reanalysis" in framing or "stored_history" in framing
    assert body["wrote"] is False
    assert "dream" not in (body.get("kind") or "").lower()
    # Structured findings may be empty for a single-session fixture; framing holds.
    assert "analysis" in body or IMAGINED_PAYLOAD_KEY in body


def test_meta_discovers_alive_paths(client: TestClient) -> None:
    root = client.get("/").json()
    assert "/v1/imagination" in root["imagination"]
    assert "/v1/memory" in root["memory"]
    assert "/v1/dream" in root["dream"]

    agent = client.get("/v1/agent").json()
    assert agent["imagination"]["path"].startswith("/v1/imagination")
    assert agent["memory"]["path"] == "/v1/memory"
    assert agent["dream"]["path"] == "/v1/dream"
    assert "CURIOSITY_NO_MEMORY" in agent["memory"]["note"]

    tools = client.get("/v1/agent/tools").json()
    fallbacks = tools["http_fallbacks"]
    assert fallbacks["list_imagination_kinds"] == "GET /v1/imagination"
    assert fallbacks["imagine_transfer"] == "POST /v1/imagination/transfer"
    assert fallbacks["memory_show"] == "GET /v1/memory"
    assert fallbacks["dream_reanalyze"] == "POST /v1/dream"
