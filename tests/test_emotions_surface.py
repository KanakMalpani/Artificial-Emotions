"""Public emotions / epistemic surface (API, Python, MCP handlers)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from artificial_curiosity import annotate_epistemic, emotion_pack, list_epistemic_cues
from artificial_curiosity.agent_tools import dispatch_tool
from artificial_curiosity.api import app
from artificial_curiosity.emotions import elicit_helpers
from artificial_curiosity.epistemic_cues import TAG_INFORMATION_GAP, TAG_SURPRISE_SIGNAL


def test_list_epistemic_cues_python():
    out = list_epistemic_cues()
    assert "information_gap" in out["tags"]
    assert out["honesty"] == "annotation_only"
    assert "feel" in out["disclaimer"].lower() or "feel" in out["note"].lower()


def test_annotate_epistemic_high_surprise():
    out = annotate_epistemic(
        "What remains unknown about epistemic emotion elicitation?",
        gap_status="unanswered",
        surprise=0.8,
        neglectedness=0.6,
    )
    tags = out["epistemic_cues"]["tags"]
    assert TAG_INFORMATION_GAP in tags
    assert TAG_SURPRISE_SIGNAL in tags
    assert out["inject_fragment"].startswith("epistemic_cues=")
    assert out["honesty"] == "annotation_only"


def test_emotion_pack_affective_science():
    pack = emotion_pack("affective_science")
    assert pack["count"] >= 8
    assert pack["name"] == "affective_science"
    assert any("epistemic" in " ".join(q["tags"]) for q in pack["questions"])


def test_elicit_helpers_anti_anthropomorphism():
    h = elicit_helpers()
    assert "framing" in h
    text = (h["framing"] + h["inject_prefix"]).lower()
    assert "not" in text and ("feel" in text or "anthropomorphism" in text)


def test_api_emotions_cues_and_annotate():
    client = TestClient(app)
    cues = client.get("/v1/emotions/cues")
    assert cues.status_code == 200
    assert "information_gap" in cues.json()["tags"]

    alias = client.get("/v1/epistemic/cues")
    assert alias.status_code == 200
    assert alias.json()["tags"] == cues.json()["tags"]

    ann = client.post(
        "/v1/emotions/annotate",
        json={
            "question": "What remains unknown about epistemic emotion elicitation?",
            "surprise": 0.75,
            "gap_status": "unanswered",
        },
    )
    assert ann.status_code == 200
    assert ann.json()["epistemic_cues"]["tags"]

    get_ann = client.get(
        "/v1/emotions/annotate",
        params={
            "question": "What remains unknown about epistemic emotion elicitation?",
            "surprise": 0.75,
        },
    )
    assert get_ann.status_code == 200

    elicit = client.get("/v1/emotions/elicit")
    assert elicit.status_code == 200
    assert "framing" in elicit.json()

    pack = client.get("/v1/emotions/pack", params={"name": "affective_science"})
    assert pack.status_code == 200
    assert pack.json()["count"] >= 8


def test_api_root_mentions_emotions():
    client = TestClient(app)
    root = client.get("/").json()
    assert "emotions" in root


def test_mcp_emotion_tools():
    from artificial_curiosity.agent_tools import mcp_tool_list

    names = {t["name"] for t in mcp_tool_list()}
    assert {
        "list_epistemic_cues",
        "annotate_epistemic",
        "emotion_pack",
        "elicit_helpers",
    } <= names

    out = dispatch_tool("list_epistemic_cues", {})
    assert "tags" in out
    out = dispatch_tool(
        "annotate_epistemic",
        {
            "question": "What remains unknown about epistemic emotion elicitation?",
            "surprise": 0.7,
        },
    )
    assert out["epistemic_cues"]["tags"]
    out = dispatch_tool("emotion_pack", {"name": "affective_science"})
    assert out["count"] >= 8
