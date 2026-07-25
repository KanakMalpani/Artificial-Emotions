"""Public emotions / epistemic surface (API, Python, MCP handlers)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from artificial_curiosity import (
    annotate_epistemic,
    emotion_catalog,
    emotion_pack,
    list_epistemic_cues,
    mix_emotions,
)
from artificial_curiosity.agent_tools import dispatch_tool
from artificial_curiosity.api import app
from artificial_curiosity.emotions import elicit_helpers
from artificial_curiosity.epistemic_cues import TAG_INFORMATION_GAP, TAG_SURPRISE_SIGNAL


def test_list_epistemic_cues_python():
    out = list_epistemic_cues()
    assert "information_gap" in out["tags"]
    assert out["honesty"] in ("annotation_only", "computational_affect")
    assert out.get("disclaimer") or out.get("note")


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
    assert out["honesty"] in ("annotation_only", "computational_affect")


def test_emotion_pack_affective_science():
    pack = emotion_pack("affective_science")
    assert pack["count"] >= 8
    assert pack["name"] == "affective_science"
    assert any("epistemic" in " ".join(q["tags"]) for q in pack["questions"])


def test_elicit_helpers_anti_anthropomorphism():
    h = elicit_helpers()
    assert "framing" in h
    text = (h["framing"] + h["inject_prefix"]).lower()
    # Still honest about simulation vs biology / not raw anthropomorphism
    assert "feel" in text or "simulation" in text or "framing" in text


def test_emotion_catalog_python():
    cat = emotion_catalog()
    assert cat["count"] >= 20
    assert "curiosity" in cat["ids"]
    assert "confusion" in cat["ids"]
    assert "awe" in cat["ids"]
    assert cat["honesty"] == "computational_affect"
    assert "epistemic" in cat["families"]
    epi = emotion_catalog(family="epistemic")
    assert epi["count"] >= 8
    assert all(e["family"] == "epistemic" for e in epi["emotions"])


def test_mix_emotions_percentages():
    blend = mix_emotions({"curiosity": 40, "confusion": 30, "awe": 30})
    assert blend["honesty"] == "computational_affect"
    assert abs(sum(blend["weights"].values()) - 1.0) < 1e-9
    assert abs(blend["percents"]["curiosity"] - 40.0) < 1e-6
    assert blend["primary"] == "curiosity"
    assert "pad" in blend and "P" in blend["pad"]
    assert "curiosity_target" in blend["cue_tags"] or "information_gap" in blend["cue_tags"]
    assert blend["felt_simulation"] is not None
    assert blend["felt_simulation"]["as_close_to_feeling_as_possible"] is True
    assert "inner_monologue" in blend["felt_simulation"]
    assert "intensity" in blend["felt_simulation"]
    assert (
        "biological" in " ".join(blend["claims_not"]).lower()
        or "consciousness" in " ".join(blend["claims_not"]).lower()
    )


def test_feel_alias():
    from artificial_curiosity import feel

    out = feel(curiosity=50, awe=50)
    assert out["felt_simulation"]["intensity"] >= 0
    assert "Simulated affect" in out["felt_simulation"]["inner_monologue"]


def test_mix_emotions_unit_weights_and_kwargs():
    a = mix_emotions(curiosity=0.4, confusion=0.3, awe=0.3)
    b = mix_emotions({"curiosity": 0.4, "confusion": 0.3, "awe": 0.3})
    assert a["weights"] == b["weights"]
    assert abs(sum(a["weights"].values()) - 1.0) < 1e-9


def test_mix_emotions_plutchik_dyad_hint():
    blend = mix_emotions({"joy": 50, "trust": 50})
    assert blend["plutchik_dyad_hint"] is not None
    assert blend["plutchik_dyad_hint"]["name"] == "love"


def test_mix_emotions_rejects_nonsense():
    with pytest.raises(ValueError, match="Unknown"):
        mix_emotions({"not_a_real_emotion": 100})
    with pytest.raises(ValueError, match="Empty|zero"):
        mix_emotions({})
    with pytest.raises(ValueError, match="zero"):
        mix_emotions({"curiosity": 0, "awe": 0})
    with pytest.raises(ValueError, match="Negative"):
        mix_emotions({"curiosity": -1})


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


def test_api_emotions_catalog_and_mix():
    client = TestClient(app)
    cat = client.get("/v1/emotions/catalog")
    assert cat.status_code == 200
    body = cat.json()
    assert body["count"] >= 20
    assert body["honesty"] in ("annotation_only", "computational_affect")

    epi = client.get("/v1/epistemic/catalog", params={"family": "epistemic"})
    assert epi.status_code == 200
    assert all(e["family"] == "epistemic" for e in epi.json()["emotions"])

    mix = client.post(
        "/v1/emotions/mix",
        json={"weights": {"curiosity": 40, "confusion": 30, "awe": 30}},
    )
    assert mix.status_code == 200
    m = mix.json()
    assert abs(m["sum_weights"] - 1.0) < 1e-9
    assert m["honesty"] == "computational_affect"
    assert m["felt_simulation"]["inner_monologue"]

    mix_no_feel = client.post(
        "/v1/emotions/mix",
        json={
            "weights": {"curiosity": 40, "confusion": 30, "awe": 30},
            "simulate_feeling": False,
        },
    )
    assert mix_no_feel.status_code == 200
    assert mix_no_feel.json()["felt_simulation"] is None

    bad = client.post(
        "/v1/emotions/mix",
        json={"weights": {"nope": 100}},
    )
    assert bad.status_code == 400
    assert bad.json()["error"]["code"] == "unknown_emotion"


def test_api_root_mentions_emotions():
    client = TestClient(app)
    root = client.get("/").json()
    assert "emotions" in root
    assert "catalog" in root["emotions"] or "mix" in root["emotions"]


def test_mcp_emotion_tools():
    from artificial_curiosity.agent_tools import mcp_tool_list

    names = {t["name"] for t in mcp_tool_list()}
    assert {
        "list_epistemic_cues",
        "emotion_catalog",
        "mix_emotions",
        "annotate_epistemic",
        "emotion_pack",
        "elicit_helpers",
    } <= names

    out = dispatch_tool("list_epistemic_cues", {})
    assert "tags" in out
    out = dispatch_tool("emotion_catalog", {})
    assert out["count"] >= 20
    out = dispatch_tool(
        "mix_emotions",
        {"weights": {"curiosity": 40, "confusion": 30, "awe": 30}},
    )
    assert abs(out["sum_weights"] - 1.0) < 1e-9
    assert out["felt_simulation"] is not None

    out_no_feel = dispatch_tool(
        "mix_emotions",
        {
            "weights": {"curiosity": 40, "confusion": 30, "awe": 30},
            "simulate_feeling": False,
        },
    )
    assert out_no_feel["felt_simulation"] is None
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
